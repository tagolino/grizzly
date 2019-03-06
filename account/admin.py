from django.contrib import admin

from account.models import Member, Staff


class StaffAdmin(admin.ModelAdmin):
    list_display = ('username', 'user', 'status',
                    'is_logged_in', 'created_by', 'updated_by')


class MemberAdmin(admin.ModelAdmin):
    list_display = ('username', 'created_by', 'created_at')


admin.site.register(Staff, StaffAdmin)
admin.site.register(Member, MemberAdmin)
