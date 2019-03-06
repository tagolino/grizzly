import django_filters

from account.models import Member


class MemberFilters(django_filters.FilterSet):
    username = django_filters.CharFilter(field_name='username',
                                         lookup_expr='exact')
    username_q = django_filters.CharFilter(field_name='username',
                                           lookup_expr='contains')
    created_at = django_filters.DateFromToRangeFilter()
    updated_at = django_filters.DateFromToRangeFilter()

    class Meta:
        model = Member
        fields = ('username',)
