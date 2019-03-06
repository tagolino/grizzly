import re

from django.utils.translation import ugettext as _
from rest_framework import serializers

from grizzly.lib import constants
from promotion.models import (Announcement,
                              Promotion,
                              PromotionElement,
                              PromotionBet,
                              PromotionBetLevel,
                              PromotionBetMonthly,
                              PromotionClaim,
                              Summary)


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


class PromotionElementAdminListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        promotion_elements = [
            PromotionElement(**item) for item in validated_data]
        return PromotionElement.objects.bulk_create(promotion_elements)


class PromotionElementAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionElement
        fields = '__all__'
        list_serializer_class = PromotionElementAdminListSerializer


class PromotionAdminSerializer(serializers.ModelSerializer):
    elements = PromotionElementAdminSerializer(many=True,
                                               read_only=True,
                                               source='promo_items')

    class Meta:
        model = Promotion
        fields = ('id', 'promotion_name', 'display_name', 'status', 'rank',
                  'desktop_icon', 'mobile_icon', 'rules', 'elements',
                  'created_by', 'created_at', 'updated_by', 'updated_at',)

    def create(self, validated_data):
        request = self.context['request']

        validated_data['created_by'] = request.user

        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context['request']

        validated_data['updated_by'] = request.user

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')

        created_by = instance.created_by
        ret['created_by'] = created_by.username if created_by else None
        updater = instance.updated_by
        ret['updated_by'] = updater.username if updater else None

        # remove some fields in list API
        if not request.GET.get('opt_fields'):
            del ret['desktop_icon'], ret['mobile_icon'], ret['rules'], \
                ret['elements']

        return ret


class PromotionElementMemberSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='get_type_display')

    class Meta:
        model = PromotionElement
        fields = ('name', 'is_required', 'display_name', 'type', 'value', 'placeholder', 'memo')


class PromotionMemberSerializer(serializers.ModelSerializer):
    elements = PromotionElementMemberSerializer(many=True,
                                                read_only=True,
                                                source='promo_items')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        context = kwargs['context']

        if context.get('list', False):
            self.fields.pop('elements')
            self.fields.pop('rules')

    class Meta:
        model = Promotion
        fields = ('id', 'promotion_name', 'display_name', 'desktop_icon', 'mobile_icon', 'rules', 'elements')


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

        block_list_sql_commands = 'CREATE|SELECT|DELETE|UPDATE|TRUNCATE|DROP| \
                                   INSERT|ALTER'
        for key, value in validated_data.get('claim_forms').items():
            if isinstance(value, str) and (
                    re.findall('[^-\w]', value) or
                    re.search(block_list_sql_commands, value, re.IGNORECASE)):
                raise serializers.ValidationError(
                    {constants.FIELD_ERROR: key})

        return super().create(validated_data)


class PromotionBetLevelAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionBetLevel
        fields = '__all__'


class PromotionBetAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionBet
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

        fields_expand = request.GET.get('opt_expand')
        if fields_expand:
            if instance.promotion_bet_level and \
                    'promotion_bet_level' in fields_expand:
                ret['promotion_bet_level'] = {
                    'id': instance.promotion_bet_level.id,
                    'name': instance.promotion_bet_level.name,
                    'total_bet': instance.promotion_bet_level.total_bet,
                    'bonus': instance.promotion_bet_level.bonus,
                    'weekly_bonus': instance.promotion_bet_level.weekly_bonus,
                    'monthly_bonus': instance.promotion_bet_level.monthly_bonus
                }

        creator = instance.created_by
        ret['created_by'] = creator.username if creator else None
        updater = instance.updated_by
        ret['updated_by'] = updater.username if updater else None

        return ret


class PromotionBetMonthlyAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionBetMonthly
        exclude = ('cycle_year', 'cycle_month')

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')

        fields_expand = request.GET.get('opt_expand')
        if fields_expand:
            ret['member'] = {
                'id': instance.member.id,
                'username': instance.member.username
            }

            if instance.promotion_bet_level:
                ret['promotion_bet_level'] = {
                    'id': instance.promotion_bet_level.id,
                    'name': instance.promotion_bet_level.name,
                    'total_bet': instance.promotion_bet_level.total_bet,
                    'bonus': instance.promotion_bet_level.bonus,
                    'weekly_bonus': instance.promotion_bet_level.weekly_bonus,
                    'monthly_bonus': instance.promotion_bet_level.monthly_bonus
                }

        return ret


class PromotionBetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionBet
        fields = ('username', 'amount', 'created_at', 'updated_at',
                  'promotion_bet_level', 'memo', 'game_type',)

    def to_representation(self, instance):
        ret = {
            'id': instance.id,
            'username': instance.username,
            'amount': instance.amount,
            'promotion_bet_level': None,
            'bonus': 0.0,
            'weekly_bonus': 0.0,
            'monthly_bonus': 0.0,
            'cycle_begin': instance.cycle_begin,
            'cycle_end': instance.cycle_end,
            'game_type': instance.game_type,
        }

        if instance.promotion_bet_level:
            ret['promotion_bet_level'] = instance.promotion_bet_level.name
            ret['bonus'] = instance.promotion_bet_level.bonus
            ret['weekly_bonus'] = instance.promotion_bet_level.weekly_bonus
            ret['monthly_bonus'] = instance.promotion_bet_level.monthly_bonus

        return ret


class PromotionBetMonthlySerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionBetMonthly
        fields = ('id', 'member', 'game_type', 'total_bet',
                  'promotion_bet_level', 'cycle_begin', 'cycle_end')

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')

        fields_expand = request.GET.get('opt_expand')
        if fields_expand:
            if 'member' in fields_expand:
                ret['member'] = {
                    'id': instance.member.id,
                    'username': instance.member.username
                }

            if instance.promotion_bet_level and \
                    'promotion_bet_level' in fields_expand:
                ret['promotion_bet_level'] = {
                    'id': instance.promotion_bet_level.id,
                    'name': instance.promotion_bet_level.name,
                    'total_bet': instance.promotion_bet_level.total_bet,
                    'bonus': instance.promotion_bet_level.bonus,
                    'weekly_bonus': instance.promotion_bet_level.weekly_bonus,
                    'monthly_bonus': instance.promotion_bet_level.monthly_bonus
                }

        return ret


class PromotionBetLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionBetLevel
        fields = ('id', 'name', 'total_bet', 'bonus',
                  'weekly_bonus', 'monthly_bonus')


class SummaryAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Summary
        fields = '__all__'

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')

        fields_expand = request.GET.get('opt_expand')
        if fields_expand:
            ret['member'] = {
                'id': instance.member.id,
                'username': instance.member.username
            }

            if instance.promotion_bet_level:
                promotion_bet_level = instance.promotion_bet_level
                ret['promotion_bet_level'] = {
                    'id': promotion_bet_level.id,
                    'name': promotion_bet_level.name,
                    'total_bet': promotion_bet_level.total_bet,
                    'bonus': promotion_bet_level.bonus,
                    'weekly_bonus': promotion_bet_level.weekly_bonus,
                    'monthly_bonus': promotion_bet_level.monthly_bonus
                }

            if instance.previous_week_bet_level:
                previous_week_bet_level = instance.previous_week_bet_level
                ret['previous_week_bet_level'] = {
                    'id': previous_week_bet_level.id,
                    'name': previous_week_bet_level.name,
                    'total_bet': previous_week_bet_level.total_bet,
                    'bonus': previous_week_bet_level.bonus,
                    'weekly_bonus': previous_week_bet_level.weekly_bonus,
                    'monthly_bonus': previous_week_bet_level.monthly_bonus
                }

            if instance.previous_month_bet_level:
                previous_month_bet_level = instance.previous_month_bet_level
                ret['previous_month_bet_level'] = {
                    'id': previous_month_bet_level.id,
                    'name': previous_month_bet_level.name,
                    'total_bet': previous_month_bet_level.total_bet,
                    'bonus': previous_month_bet_level.bonus,
                    'weekly_bonus': previous_month_bet_level.weekly_bonus,
                    'monthly_bonus': previous_month_bet_level.monthly_bonus
                }

        return ret


class SummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Summary
        fields = ('member', 'promotion_bet_level', 'total_promotion_bet',
                  'total_promotion_bonus', 'game_type',)

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

            if 'member' in fields_expand:
                ret['member'] = {
                    'id': instance.member.id,
                    'username': instance.member.username,
                    'memo': instance.member.memo,
                    'created_at': instance.member.created_at,
                }

        if instance.promotion_bet_level:
            bet_level = PromotionBetLevel.objects.filter(
                total_bet__gt=instance.promotion_bet_level.total_bet)

            if bet_level.exists():
                bet_diff = bet_level.first().total_bet - \
                    instance.total_promotion_bet
                ret['bets_to_next_level'] = bet_diff

        return ret
