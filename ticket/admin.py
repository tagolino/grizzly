from django.contrib import admin

from ticket.models import Ticket


class TicketAdmin(admin.ModelAdmin):
    list_display = ('username', 'activity', 'status', 'created_at',
                    'updated_by')

admin.site.register(Ticket, TicketAdmin)
