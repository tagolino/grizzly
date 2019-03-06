from rest_framework import serializers

from envelope.models import (EnvelopeLevel,
                             EnvelopeDeposit,
                             EnvelopeClaim,
                             EnvelopeAmountSetting)


class EnvelopeClaimMemberSerializer(serializers.ModelSerializer):

    class Meta:
        model = EnvelopeClaim
        fields = ('id', 'username', 'amount', 'envelope_type',
                  'status', 'created_at')

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['claim_left'] = EnvelopeClaim.objects.get_quantity_left(
            instance.username, instance.envelope_type)

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
