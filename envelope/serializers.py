from rest_framework import serializers

from envelope.models import (EnvelopeLevel,
                             EnvelopeDeposit,
                             EnvelopeClaim,
                             EnvelopeAmountSetting,
                             RequestLog,
                             EventType,
                             Reward)


class EnvelopeClaimMemberSerializer(serializers.ModelSerializer):

    class Meta:
        model = EnvelopeClaim
        fields = ('id', 'username', 'amount', 'reward',
                  'event_type', 'status', 'created_at')

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        fields_expand = request.GET.get('opt_expand', '')

        ret['claim_left'] = EnvelopeClaim.objects.get_quantity_left(
            instance.username, instance.event_type)

        if instance.reward and 'reward' in fields_expand:
            ret['reward'] = {
                'id': instance.reward_id,
                'name': instance.reward.name
            }

        return ret


class EnvelopeClaimAdminSerializer(serializers.ModelSerializer):

    class Meta:
        model = EnvelopeClaim
        fields = '__all__'

    def update(self, instance, validated_data):
        request = self.context['request']

        validated_data['updated_by'] = request.user

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        updater = instance.updated_by
        ret['updated_by'] = updater.username if updater else None

        if instance.reward:
            ret['reward'] = {
                'id': instance.reward_id,
                'name': instance.reward.name
            }

        return ret


class EnvelopeDepositAdminSerializer(serializers.ModelSerializer):

    class Meta:
        model = EnvelopeDeposit
        fields = '__all__'

    def update(self, instance, validated_data):

        request = self.context['request']

        validated_data['updated_by'] = request.user

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        creator = instance.created_by
        ret['created_by'] = creator.username if creator else None
        updater = instance.updated_by
        ret['updated_by'] = updater.username if updater else None

        return ret


class EnvelopeLevelAdminSerializer(serializers.ModelSerializer):

    class Meta:
        model = EnvelopeLevel
        fields = '__all__'


class EnvelopeLevelMemberSerializer(serializers.ModelSerializer):

    class Meta:
        model = EnvelopeLevel
        fields = ('name', 'amount', 'quantity')


class EnvelopeSettingAdminSerializer(serializers.ModelSerializer):

    class Meta:
        model = EnvelopeAmountSetting
        fields = '__all__'

    def update(self, instance, validated_data):

        request = self.context['request']

        validated_data['updated_by'] = request.user

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        creator = instance.created_by
        ret['created_by'] = creator.username if creator else None
        updater = instance.updated_by
        ret['updated_by'] = updater.username if updater else None

        return ret


class EnvelopeDepositMemberSerializer(serializers.ModelSerializer):

    class Meta:
        model = EnvelopeDeposit
        fields = ('username', 'event_type', 'amount', 'created_at')


class RewardAdminSerializer(serializers.ModelSerializer):

    class Meta:
        model = Reward
        fields = '__all__'


class RewardMemberSerializer(serializers.ModelSerializer):

    class Meta:
        model = Reward
        fields = ('id', 'name', 'event_type', 'amount', 'chance',
                  'created_at')


class EventTypeAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventType
        fields = '__all__'

    def update(self, instance, validated_data):
        validated_keys = validated_data.keys()
        if 'is_active' in validated_keys:
            instance.is_active = validated_data.get('is_active')

        if 'memo' in validated_keys:
            instance.memo = validated_data.get('memo')

        instance.save()

        return instance


class EventTypeMemberSerializer(serializers.ModelSerializer):

    class Meta:
        model = EventType
        fields = ('name', 'date_from', 'time_from', 'date_to',
                  'time_to', 'memo', 'is_active')


class RequestLogAdminSerializer(serializers.ModelSerializer):

    class Meta:
        model = RequestLog
        fields = '__all__'

    def create(self, validated_data):
        '''
        '''

        request = self.context['request']

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

        creator = instance.created_by
        ret['created_by'] = creator.username if creator else None

        return ret
