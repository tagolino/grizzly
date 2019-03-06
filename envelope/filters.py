import django_filters

from envelope.models import (EnvelopeAmountSetting,
                             EnvelopeDeposit,
                             EnvelopeClaim,
                             EnvelopeLevel)


class EnvelopeClaimFilter(django_filters.FilterSet):
    '''
    '''
    username = django_filters.CharFilter(field_name='username',
                                         lookup_expr='exact')
    username_q = django_filters.CharFilter(field_name='username',
                                           lookup_expr='contains')
    status = django_filters.NumberFilter(field_name='status',
                                         lookup_expr='exact')
    type = django_filters.NumberFilter(field_name='envelope_type',
                                       lookup_expr='exact')
    created_at = django_filters.DateFromToRangeFilter()
    updated_at = django_filters.DateFromToRangeFilter()
    updated_by = django_filters.CharFilter(field_name='updated_by__username',
                                           lookup_expr='contains')

    class Meta:
        model = EnvelopeClaim
        fields = ('username', 'status', 'envelope_type', 'created_at',
                  'updated_at', 'updated_by')


class EnvelopeDepositFilter(django_filters.FilterSet):
    username = django_filters.CharFilter(field_name='username',
                                         lookup_expr='exact')
    username_q = django_filters.CharFilter(field_name='username',
                                           lookup_expr='contains')
    type = django_filters.NumberFilter(field_name='envelope_type',
                                       lookup_expr='exact')
    created_at = django_filters.DateFromToRangeFilter()
    created_by = django_filters.CharFilter(field_name='created_by__username',
                                           lookup_expr='contains')
    updated_at = django_filters.DateFromToRangeFilter()
    updated_by = django_filters.CharFilter(field_name='updated_by__username',
                                           lookup_expr='contains')

    class Meta:
        model = EnvelopeDeposit
        fields = ('username', 'envelope_type',)


class EnvelopeAmountSettingFilter(django_filters.FilterSet):
    type = django_filters.NumberFilter(field_name='envelope_type',
                                       lookup_expr='exact')

    class Meta:
        model = EnvelopeAmountSetting
        fields = ('envelope_type',)


class EnvelopeLevelFilter(django_filters.FilterSet):
    type = django_filters.NumberFilter(field_name='envelope_type',
                                       lookup_expr='exact')

    class Meta:
        model = EnvelopeLevel
        fields = ('envelope_type',)
