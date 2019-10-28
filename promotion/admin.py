from datetime import datetime, timedelta
from django.conf.urls import url
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.utils import timezone

from promotion.models import (Announcement,
                              Promotion,
                              PromotionElement,
                              PromotionClaim,
                              PromotionBet,
                              PromotionBetLevel,
                              PromotionBetMonthly,
                              ImportExportLog,
                              Summary)
from promotion.tasks import compute_total_bonus


class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('name', 'announcement', 'status',
                    'rank', 'platform')


class PromotionAdmin(admin.ModelAdmin):
    list_display = ('promotion_name', 'display_name', 'status', 'rank',)


class PromotionClaimAdmin(admin.ModelAdmin):
    list_display = ('username', 'promotion_id', 'game_name',
                    'status', 'created_by')


class PromotionBetAdmin(admin.ModelAdmin):
    list_display = ('member', 'cycle_begin', 'cycle_end', 'amount',
                    'promotion_bet_level', 'game_type', 'created_by',
                    'created_at', 'active')


class PromotionBetLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'game_type', 'total_bet', 'bonus', 'weekly_bonus',
                    'monthly_bonus')


class PromotionBetMonthlyAdmin(admin.ModelAdmin):
    list_display = ('member', 'game_type', 'cycle_year', 'cycle_month',
                    'total_bet', 'accumulated_bonus', 'total_weekly_bonus',
                    'month_bonus')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            url(r'^compute-total-bonus/$', self.compute_total_bonus,
                name='compute_total_bonus')
        ]
        return custom_urls + urls

    def compute_total_bonus(self, request):
        compute_total_bonus.apply_async(None,
                                        queue='bet_operations')

        messages.success(
            request,
            f'Compute members total bonus requested.'
        )

        return redirect('/admin/promotion/promotionbetmonthly/')


class SummaryAdmin(admin.ModelAdmin):
    list_display = ('member', 'game_type', 'promotion_bet_level',
                    'previous_week_bet_level', 'previous_month_bet_level',
                    'total_promotion_bet', 'current_week_bonus',
                    'total_bonus', 'created_at', 'updated_at')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            url(r'^update_data/$', self.update_summary_bet_data,
                name='update_summary_data')
        ]
        return custom_urls + urls

    def update_summary_bet_data(self, request):
        today = timezone.localtime(timezone.now())
        week_begin = (today - timedelta(days=today.weekday())).date()
        week_end = week_begin + timedelta(days=6)
        members = Summary.objects.filter(
            updated_at__date__lt=week_begin,
            promotion_bet_level__isnull=False
        )

        for member in members:
            update_fields = []
            if not member.promotion_bet_level == \
                    member.previous_week_bet_level:
                member.previous_week_bet_level = member.promotion_bet_level
                member.current_week_bonus = 0

                update_fields.extend(
                    ['previous_week_bet_level', 'current_week_bonus'])

            if member.updated_at.month <= \
                    (today - timedelta(days=today.day)).month:
                member.previous_month_bet_level = member.promotion_bet_level
                update_fields.append('previous_month_bet_level')

            if update_fields:
                member.updated_at = today
                update_fields.append('updated_at')

            member.save(update_fields=update_fields)

        messages.success(
            request,
            f'{members.count()} members promotion bet summary updated.'
        )

        return redirect('/admin/promotion/summary/')


class ImportExportLogAdmin(admin.ModelAdmin):
    list_display = ('game_type', 'request_type', 'status', 'filename',
                    'memo', 'created_by', 'created_at', 'updated_at')


admin.site.register(Announcement, AnnouncementAdmin)
admin.site.register(Promotion, PromotionAdmin)
admin.site.register(PromotionElement)
admin.site.register(PromotionClaim, PromotionClaimAdmin)
admin.site.register(PromotionBet, PromotionBetAdmin)
admin.site.register(PromotionBetLevel, PromotionBetLevelAdmin)
admin.site.register(PromotionBetMonthly, PromotionBetMonthlyAdmin)
admin.site.register(Summary, SummaryAdmin)
admin.site.register(ImportExportLog, ImportExportLogAdmin)
