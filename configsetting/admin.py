from django.contrib import admin
from django.utils.html import format_html
from configsetting.models import GlobalPreference


class GlobalPreferenceAdmin(admin.ModelAdmin):
    list_display = ('key', '_value')
    readonly_fields = ('_value',)

    def _value(self, obj):
        if obj.type == GlobalPreference.TYPE_IMAGE:
            img = obj.image
            if img and hasattr(img, 'url'):
                return format_html(f'<img width="48" src="{obj.image.url}" />')
            return None
        else:
            return obj.value
    _value.short_description = 'Image'


admin.site.register(GlobalPreference, GlobalPreferenceAdmin)
