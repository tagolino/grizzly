import re

from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from account.models import Staff
from grizzly.lib import constants
from grizzly.utils import create_otp_device


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
