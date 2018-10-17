from django.utils.translation import ugettext as _
from rest_framework import serializers

from grizzly.lib import constants
from promotion.models import (Announcement,
                              PromotionClaim)


class AnnouncementAdminSerializer(serializers.ModelSerializer):
    '''
    '''

    class Meta:
        model = Announcement
        fields = '__all__'

    def update(self, instance, validated_data):
        '''
        '''

        request = self.context['request']

        validated_data['updated_by'] = request.user

        return super().update(instance, validated_data)

    def create(self, validated_data):
        request = self.context['request']

        if validated_data.get('announcement') is None:
            raise serializers.\
                ValidationError({'error': _('Announcement is required')})

        # adjusts all the ranking of existing banners
        announcements = Announcement.objects.all().count()
        validated_data['rank'] = announcements + 1

        validated_data['created_by'] = request.user

        return super().create(validated_data)


class AnnouncementMemberSerializer(serializers.ModelSerializer):
    '''
    '''

    class Meta:
        model = Announcement
        fields = ('id', 'announcement', 'platform',
                  'status', 'rank', 'created_at')


class PromotionClaimAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionClaim
        fields = '__all__'

    def create(self, validated_data):
        request = self.context['request']

        if not validated_data.get('username'):
            raise serializers.ValidationError(
                {constants.REQUIRED_FIELD: 'username'})

        if not validated_data.get('promotion_id'):
            raise serializers.ValidationError(
                {constants.REQUIRED_FIELD: 'promotion_id'})

        if not validated_data.get('game_name'):
            raise serializers.ValidationError(
                {constants.REQUIRED_FIELD: 'game_name'})

        validated_data['created_by'] = request.user

        return super().create(validated_data)

    def update(self, instance, validated_data):
        '''
        '''

        request = self.context['request']

        validated_data['updated_by'] = request.user

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        updater = instance.updated_by
        ret['updated_by'] = updater.username if updater else None

        return ret


class PromotionClaimMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionClaim
        fields = ('id', 'promotion_id', 'username', 'game_name',
                  'status', 'memo', 'claim_forms', 'created_at')

    def create(self, validated_data):
        if not validated_data.get('username'):
            raise serializers.ValidationError(
                {constants.REQUIRED_FIELD: 'username'})

        if not validated_data.get('promotion_id'):
            raise serializers.ValidationError(
                {constants.REQUIRED_FIELD: 'promotion_id'})

        if not validated_data.get('game_name'):
            raise serializers.ValidationError(
                {constants.REQUIRED_FIELD: 'game_name'})

        return super().create(validated_data)
