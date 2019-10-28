from django.contrib import admin

from envelope.models import (EnvelopeClaim,
                             EnvelopeLevel,
                             EnvelopeDeposit,
                             EnvelopeAmountSetting,
                             EventType,
                             RequestLog,
                             Reward)


class EnvelopeClaimAdmin(admin.ModelAdmin):
    list_display = ('username', 'amount', 'status', 'event_type',
                    'created_at', 'created_by')


class EnvelopeLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'quantity', 'event_type')


class EnvelopeDepositAdmin(admin.ModelAdmin):
    list_display = ('username', 'amount', 'event_type', 'created_by')


class EnvelopeAmountSettingAdmin(admin.ModelAdmin):
    list_display = ('name', 'threshold_amount', 'min_amount', 'max_amount',
                    'event_type')


class RewardAdmin(admin.ModelAdmin):
    list_display = ('name', 'event_type', 'chance')


class EventTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'date_from', 'time_from', 'date_to',
                    'time_to', 'is_active')


class RequestLogAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'request_type', 'status', 'filename',
                    'memo', 'created_by', 'created_at', 'updated_at')


admin.site.register(EnvelopeClaim, EnvelopeClaimAdmin)
admin.site.register(EnvelopeLevel, EnvelopeLevelAdmin)
admin.site.register(EnvelopeDeposit, EnvelopeDepositAdmin)
admin.site.register(EnvelopeAmountSetting, EnvelopeAmountSettingAdmin)
admin.site.register(Reward, RewardAdmin)
admin.site.register(EventType, EventTypeAdmin)
admin.site.register(RequestLog, RequestLogAdmin)
