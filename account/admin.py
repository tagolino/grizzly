from datetime import datetime, timedelta
from django.conf.urls import url
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.utils import timezone

from account.models import Member, Staff
from promotion.models import GAME_TYPE_ELECTRONICS
from promotion.tasks import migrate_member_summary


class StaffAdmin(admin.ModelAdmin):
    list_display = ('username', 'user', 'status',
                    'is_logged_in', 'created_by', 'updated_by')


class MemberAdmin(admin.ModelAdmin):
    list_display = (
        'username', 'promotion_bet_level', 'previous_week_bet_level',
        'previous_month_bet_level', 'total_promotion_bet',
        'total_promotion_bonus', 'current_week_bonus', 'total_bonus',
        'created_at', 'updated_at',
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            url(r'^update_data/$', self.update_member_bet_data,
                name='update_member_data'),
            url(r'^migrate-member-summary/$', self.migrate_summary_data,
                name='migrate_summary_data')
        ]
        return custom_urls + urls

    def update_member_bet_data(self, request):
        today = timezone.localtime(timezone.now())
        week_begin = (today - timedelta(days=today.weekday())).date()
        week_end = week_begin + timedelta(days=6)
        members = Member.objects.filter(
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

        return redirect('/admin/account/member/')

    def migrate_summary_data(self, request):
        migrate_member_summary.apply_async(None,
                                           queue='bet_operations')
        messages.success(
            request,
            f'Migrating member summary requested.'
        )

        return redirect('/admin/account/member/')


admin.site.register(Staff, StaffAdmin)
admin.site.register(Member, MemberAdmin)
