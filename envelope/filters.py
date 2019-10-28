import django_filters

from envelope.models import (EnvelopeAmountSetting,
                             EnvelopeDeposit,
                             EnvelopeClaim,
                             EnvelopeLevel,
                             EventType,
                             RequestLog,
                             Reward)


class EnvelopeClaimFilter(django_filters.FilterSet):
    '''
    '''
    username = django_filters.CharFilter(field_name='username',
                                         lookup_expr='exact')
    username_q = django_filters.CharFilter(field_name='username',
                                           lookup_expr='icontains')
    status = django_filters.NumberFilter(field_name='status',
                                         lookup_expr='exact')
    event_type = django_filters.CharFilter(field_name='event_type__code',
                                           lookup_expr='exact')
    created_at = django_filters.DateFromToRangeFilter()
    updated_at = django_filters.DateFromToRangeFilter()
    updated_by = django_filters.CharFilter(field_name='updated_by__username',
                                           lookup_expr='icontains')

    class Meta:
        model = EnvelopeClaim
        fields = ('username', 'status', 'event_type__code', 'created_at',
                  'updated_at', 'updated_by')


class EnvelopeDepositFilter(django_filters.FilterSet):
    username = django_filters.CharFilter(field_name='username',
                                         lookup_expr='exact')
    username_q = django_filters.CharFilter(field_name='username',
                                           lookup_expr='icontains')
    event_type = django_filters.CharFilter(field_name='event_type__code',
                                           lookup_expr='exact')
    created_at = django_filters.DateFromToRangeFilter()
    created_by = django_filters.CharFilter(field_name='created_by__username',
                                           lookup_expr='icontains')
    updated_at = django_filters.DateFromToRangeFilter()
    updated_by = django_filters.CharFilter(field_name='updated_by__username',
                                           lookup_expr='icontains')

    class Meta:
        model = EnvelopeDeposit
        fields = ('username', 'event_type__code',)


class EnvelopeAmountSettingFilter(django_filters.FilterSet):
    event_type = django_filters.CharFilter(field_name='event_type__code',
                                           lookup_expr='exact')

    class Meta:
        model = EnvelopeAmountSetting
        fields = ('event_type__code',)


class EnvelopeLevelFilter(django_filters.FilterSet):
    event_type = django_filters.CharFilter(field_name='event_type__code',
                                           lookup_expr='exact')

    class Meta:
        model = EnvelopeLevel
        fields = ('event_type__code',)


class RewardFilter(django_filters.FilterSet):
    event_type = django_filters.CharFilter(field_name='event_type__code',
                                           lookup_expr='exact')

    class Meta:
        model = Reward
        fields = ('event_type__code',)


class EventTypeFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name='name',
                                     lookup_expr='exact')
    name_q = django_filters.CharFilter(field_name='name',
                                       lookup_expr='icontains')
    code = django_filters.CharFilter(field_name='code',
                                     lookup_expr='exact')
    status = django_filters.NumberFilter(field_name='is_active',
                                         lookup_expr='exact')

    class Meta:
        model = EventType
        fields = ('name', 'code', 'is_active')


class RequestLogFilter(django_filters.FilterSet):
    request_type = django_filters.NumberFilter(field_name='request_type',
                                               lookup_expr='exact')
    status = django_filters.NumberFilter(field_name='status',
                                         lookup_expr='exact')
    filename = django_filters.CharFilter(field_name='filename',
                                         lookup_expr='exact')
    filename_q = django_filters.CharFilter(field_name='filename',
                                           lookup_expr='icontains')
    created_by = django_filters.CharFilter(field_name='created_by__username',
                                           lookup_expr='exact')
    created_by_q = django_filters.CharFilter(field_name='created_by__username',
                                             lookup_expr='icontains')
    created_at = django_filters.DateFromToRangeFilter()
    updated_at = django_filters.DateFromToRangeFilter()
    event_type = django_filters.CharFilter(field_name='event_type__code',
                                           lookup_expr='exact')

    class Meta:
        model = RequestLog
        fields = ('request_type', 'filename', 'status', 'created_by',
                  'created_at', 'updated_at', 'event_type',)
