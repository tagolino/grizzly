from rest_framework import serializers
from django.utils.translation import ugettext as _
from configsetting.models import GlobalPreference
from grizzly.lib import constants


class GlobalPreferencesSerializer(serializers.ModelSerializer):

    class Meta:
        model = GlobalPreference
        fields = ['key', 'type', 'value', 'display_name', 'image', 'note']

    def validate(self, data):
        key = self.context['view'].kwargs.get('key')

        # if need validation, should add method named 'validate_{key}'
        validate_function = \
            getattr(self, f'validate_{key}', self.default_validate)

        return validate_function(data)

    def default_validate(self, data):
        if self.context['request'].method == 'PATCH' and 'key' in data:
            raise serializers.ValidationError({
                constants.NOT_ALLOWED: _("Can't revise key")
            })

        if 'value' in data:
            # validate empty str
            data['value'] = data['value'].strip()
            key = self.context['view'].kwargs.get('key')

            # strip comma separated segments and store them for later usage
            # strip blanks for each comma separated sub_value
            segments = []
            for segment in data['value'].split(','):
                segments.append(segment.strip())
            data['sub_values'] = segments
            if len(data['sub_values']) > 1:
                data['value'] = ','.join(segments)

        return data

    def _validate_image(self, data):
        # value field can be blank in this case
        # only the image field is necessary for this
        if self.context['request'].method == 'PATCH' and 'key' in data:
            raise serializers.ValidationError({
                constants.NOT_ALLOWED: _("Can't revise key")
            })

        if not data.get('image', None):
            raise serializers.ValidationError({
                constants.NOT_ALLOWED: _("Can't revise key")
            })
        return data

    def validate_app_code(self, data):
        return self._validate_image(data)

    def validate_ad_header(self, data):
        return self._validate_image(data)


class GlobalPreferencesMemberSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = GlobalPreference
        fields = ['value']

    def get_value(self, instance):
        request = self.context.get('request')
        if instance.type == GlobalPreference.TYPE_IMAGE:
            img = instance.image
            if img and hasattr(img, 'url'):
                return request.build_absolute_uri(img.url)
            return None
        else:
            return instance.value
