from django.contrib import admin

from account.models import Staff


class StaffAdmin(admin.ModelAdmin):
    list_display = ('username', 'user', 'status',
                    'is_logged_in', 'created_by', 'updated_by')


admin.site.register(Staff, StaffAdmin)
