from django.contrib import admin

from promotion.models import Announcement, PromotionClaim


class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('name', 'announcement', 'status',
                    'rank', 'platform')


class PromotionClaimAdmin(admin.ModelAdmin):
    list_display = ('username', 'promotion_id', 'game_name',
                    'status', 'created_by')


admin.site.register(Announcement, AnnouncementAdmin)
admin.site.register(PromotionClaim, PromotionClaimAdmin)
