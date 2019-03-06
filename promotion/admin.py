from django.contrib import admin

from promotion.models import (Announcement,
                              Promotion,
                              PromotionElement,
                              PromotionClaim,
                              PromotionBet,
                              PromotionBetLevel,
                              PromotionBetMonthly,
                              Summary)


class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('name', 'announcement', 'status',
                    'rank', 'platform')


class PromotionAdmin(admin.ModelAdmin):
    list_display = ('promotion_name', 'display_name', 'status', 'rank',)


class PromotionClaimAdmin(admin.ModelAdmin):
    list_display = ('username', 'promotion_id', 'game_name',
                    'status', 'created_by')


class PromotionBetAdmin(admin.ModelAdmin):
    list_display = ('member', 'amount', 'promotion_bet_level',
                    'game_type', 'created_by', 'created_at')


class PromotionBetLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'game_type', 'total_bet', 'bonus', 'weekly_bonus',
                    'monthly_bonus')


class PromotionBetMonthlyAdmin(admin.ModelAdmin):
    list_display = ('member', 'game_type', 'total_bet', 'promotion_bet_level', 
                    'cycle_year', 'cycle_month')


class SummaryAdmin(admin.ModelAdmin):
    list_display = ('member', 'game_type',)


admin.site.register(Announcement, AnnouncementAdmin)
admin.site.register(Promotion, PromotionAdmin)
admin.site.register(PromotionElement)
admin.site.register(PromotionClaim, PromotionClaimAdmin)
admin.site.register(PromotionBet, PromotionBetAdmin)
admin.site.register(PromotionBetLevel, PromotionBetLevelAdmin)
admin.site.register(PromotionBetMonthly, PromotionBetMonthlyAdmin)
admin.site.register(Summary, SummaryAdmin)
