import django_filters

from promotion.models import (Announcement,
                              PromotionClaim)


class PlatformFilter(django_filters.Filter):
    '''
    '''

    def filter(self, qs, value):
        '''
        '''

        if not value:
            return qs
        # include banners for both mobile and desktop platforms
        return qs.filter(platform__in=[value, 2])


class AnnouncementFilter(django_filters.FilterSet):
    '''
    '''

    platform = PlatformFilter(field_name='platform', lookup_expr='exact')
    status = django_filters.NumberFilter(field_name='status',
                                         lookup_expr='exact')

    class Meta:
        model = Announcement
        fields = ('platform', 'status',)


class PromotionClaimFilter(django_filters.FilterSet):
    '''
    '''
    promotion_id = django_filters.CharFilter(field_name='promotion_id',
                                             lookup_expr='exact')
    promotion_id_q = django_filters.CharFilter(field_name='promotion_id',
                                               lookup_expr='contains')
    game_name = django_filters.CharFilter(field_name='game_name',
                                          lookup_expr='exact')
    game_name_q = django_filters.CharFilter(field_name='game_name',
                                            lookup_expr='contains')
    username = django_filters.CharFilter(field_name='username',
                                         lookup_expr='exact')
    username_q = django_filters.CharFilter(field_name='username',
                                           lookup_expr='contains')
    status = django_filters.NumberFilter(field_name='status',
                                         lookup_expr='exact')
    created_at = django_filters.DateFromToRangeFilter()
    updated_at = django_filters.DateFromToRangeFilter()
    updated_by = django_filters.CharFilter(field_name='updated_by__username',
                                           lookup_expr='contains')

    class Meta:
        model = PromotionClaim
        fields = ('promotion_id', 'game_name', 'status',
                  'created_at', 'updated_at', 'updated_by')
