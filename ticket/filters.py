import django_filters

from ticket.models import Ticket


class TicketFilter(django_filters.FilterSet):
    '''
    '''
    ticket_id = django_filters.CharFilter(field_name='id',
                                          lookup_expr='exact')
    username = django_filters.CharFilter(field_name='username',
                                         lookup_expr='exact')
    username_q = django_filters.CharFilter(field_name='username',
                                           lookup_expr='contains')
    activity = django_filters.NumberFilter(field_name='activity',
                                           lookup_expr='exact')
    status = django_filters.NumberFilter(field_name='status',
                                         lookup_expr='exact')
    updated_by = django_filters.CharFilter(field_name='updated_by__username',
                                           lookup_expr='contains')
    created_at = django_filters.DateFromToRangeFilter()
    updated_at = django_filters.DateFromToRangeFilter()

    class Meta:
        model = Ticket
        fields = ('id', 'username', 'activity', 'status', 'updated_by',
                  'created_at', 'updated_at')
