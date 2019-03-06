from django.contrib import admin

from envelope.models import (EnvelopeClaim,
                             EnvelopeLevel,
                             EnvelopeDeposit,
                             EnvelopeAmountSetting)


class EnvelopeClaimAdmin(admin.ModelAdmin):
    list_display = ('username', 'amount', 'status', 'envelope_type',
                    'created_at', 'created_by')


class EnvelopeLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'quantity', 'envelope_type')


class EnvelopeDepositAdmin(admin.ModelAdmin):
    list_display = ('username', 'amount', 'envelope_type', 'created_by')


class EnvelopeAmountSettingAdmin(admin.ModelAdmin):
    list_display = ('name', 'threshold_amount', 'min_amount', 'max_amount',
                    'envelope_type')


admin.site.register(EnvelopeClaim, EnvelopeClaimAdmin)
admin.site.register(EnvelopeLevel, EnvelopeLevelAdmin)
admin.site.register(EnvelopeDeposit, EnvelopeDepositAdmin)
admin.site.register(EnvelopeAmountSetting, EnvelopeAmountSettingAdmin)
