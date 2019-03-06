from rest_framework import serializers

from account.models import Member
from grizzly.lib import constants
from grizzly.utils import verify_captcha
from loginsvc.views import generate_response
from ticket.models import Ticket


class TicketAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = '__all__'

    def update(self, instance, validated_data):
        request = self.context['request']

        instance.updated_by = request.user

        status = validated_data.get('status', None)
        if status == Ticket.STATUS_APPROVED:
            member, created = Member.objects.get_or_create(
                username=instance.username
            )
            instance.member = member

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        request = self.context.get('request')
        ret = super().to_representation(instance)

        updated_by = instance.updated_by
        ret['updated_by'] = updated_by.username if updated_by else None

        fields_expand = request.GET.get('opt_expand')
        if fields_expand and 'activity' in fields_expand:
            ret['activity'] = {
                'id': instance.activity,
                'name': dict(
                    Ticket.ACTIVITY_CHOICES).get(instance.activity)
            }

        return ret


class TicketMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ('id', 'username', 'activity', 'activity_details',
                  'status', 'memo', 'created_at')

    def validate(self, data):
        """
            Verify captcha code sent in POST request.
        """

        request = self.context.get('request')
        if request.method == 'POST':
            captcha = {
                'verification_code_0': request.data.get('captcha_0', ''),
                'verification_code_1': request.data.get('captcha_1', '')
            }

            if not verify_captcha(captcha):
                raise serializers.ValidationError(constants.INCORRECT_CAPTCHA)

        return super().validate(data)
