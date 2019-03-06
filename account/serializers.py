import re

from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from account.models import Staff, Member
from grizzly.lib import constants
from grizzly.utils import create_otp_device
from promotion.models import PromotionBetLevel


class StaffSerializer(serializers.ModelSerializer):
    '''
    Create, update for staff groups
    '''

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        request = self.context.get('request')
        ret['password'] = request.data.get('password')
        return ret

    def validate(self, data):
        request = self.context.get('request')
        if request.method == 'POST':
            username = data.get('username')
            if not re.match('^[a-zA-Z0-9]{6,15}$', username):
                raise serializers.ValidationError(constants.INVALID_USERNAME)
            try:
                staff = Staff.objects.get(username=username)
                user = User.objects.get(username=username)
                raise serializers.ValidationError(constants.USERNAME_IN_USED)
            except ObjectDoesNotExist:
                pass
        return data

    def update(self, instance, validated_data):
        '''
        '''

        request = self.context['request']
        updater = request.user
        # Change staff password
        if validated_data.get('password'):
            new_password = validated_data['password']
            instance.user.set_password(new_password)
            instance.user.save()

        validated_data['updated_by'] = updater

        return super().update(instance, validated_data)

    def create(self, validated_data):
        '''
        '''

        request = self.context['request']
        creator = request.user
        username = validated_data.get('username')
        password = validated_data.pop('password')
        role = Group.objects.filter(name='staff_grp').first()

        staff = Staff.objects.create(**validated_data)
        if staff:
            user = User.objects.create_user(username=username,
                                            password=password,
                                            email=None)
            user.groups.add(role)
            staff.user = user
            staff.created_by = creator
            staff.save()

            # create otp device
            create_otp_device(user)
            return staff

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        creator = instance.created_by
        ret['created_by'] = creator.username if creator else None
        updater = instance.updated_by
        ret['updated_by'] = updater.username if updater else None

        return ret

    class Meta:
        model = Staff
        fields = '__all__'


class MemberAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = '__all__'

    def update(self, instance, validated_data):
        '''
        '''

        request = self.context['request']
        updater = request.user

        validated_data['updated_by'] = updater

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        request = self.context.get('request')
        ret = super().to_representation(instance)

        creator = instance.created_by
        ret['created_by'] = creator.username if creator else None
        updater = instance.updated_by
        ret['updated_by'] = updater.username if updater else None

        fields_expand = request.GET.get('opt_expand')
        if fields_expand:
            if instance.promotion_bet_level:
                ret['promotion_bet_level'] = {
                    'id': instance.promotion_bet_level.id,
                    'name': instance.promotion_bet_level.name,
                    'total_bet': instance.promotion_bet_level.total_bet,
                    'bonus': instance.promotion_bet_level.bonus,
                    'weekly_bonus': instance.promotion_bet_level.weekly_bonus,
                    'monthly_bonus': instance.promotion_bet_level.monthly_bonus
                }

            if instance.previous_week_bet_level:
                ret['previous_week_bet_level'] = {
                    'id': instance.previous_week_bet_level.id,
                    'name': instance.previous_week_bet_level.name,
                    'total_bet': instance.previous_week_bet_level.total_bet,
                    'bonus': instance.previous_week_bet_level.bonus,
                    'weekly_bonus': instance.previous_week_bet_level.weekly_bonus,
                    'monthly_bonus': instance.previous_week_bet_level.monthly_bonus
                }

            if instance.previous_month_bet_level:
                ret['previous_month_bet_level'] = {
                    'id': instance.previous_week_bet_level.id,
                    'name': instance.previous_month_bet_level.name,
                    'total_bet': instance.previous_month_bet_level.total_bet,
                    'bonus': instance.previous_month_bet_level.bonus,
                    'weekly_bonus': instance.previous_month_bet_level.weekly_bonus,
                    'monthly_bonus': instance.previous_month_bet_level.monthly_bonus
                }

        return ret


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ('username', 'promotion_bet_level', 'total_promotion_bet',
                  'total_promotion_bonus', 'created_at', 'memo')

    def to_representation(self, instance):
        request = self.context.get('request')
        ret = super().to_representation(instance)

        ret['bets_to_next_level'] = 0.0

        fields_expand = request.GET.get('opt_expand')
        if fields_expand:
            if instance.promotion_bet_level and \
                    'promotion_bet_level' in fields_expand:
                ret['promotion_bet_level'] = {
                    'id': instance.promotion_bet_level.id,
                    'name': instance.promotion_bet_level.name,
                    'weekly_bonus': instance.promotion_bet_level.weekly_bonus,
                    'monthly_bonus': instance.promotion_bet_level.monthly_bonus
                }

        if instance.promotion_bet_level:
            bet_level = PromotionBetLevel.objects.filter(
                total_bet__gt=instance.promotion_bet_level.total_bet)

            if bet_level.exists():
                bet_diff = bet_level.first().total_bet - \
                    instance.total_promotion_bet
                ret['bets_to_next_level'] = bet_diff

        return ret
