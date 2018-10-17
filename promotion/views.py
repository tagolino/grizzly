from rest_condition import Or
from rest_framework import mixins, viewsets

from grizzly.utils import GrizzlyRenderer
from loginsvc.permissions import IsAdmin, IsStaff
from promotion.filters import (AnnouncementFilter,
                               PromotionClaimFilter)
from promotion.models import (Announcement,
                              PromotionClaim)
from promotion.serializers import (AnnouncementAdminSerializer,
                                   AnnouncementMemberSerializer,
                                   PromotionClaimAdminSerializer,
                                   PromotionClaimMemberSerializer)


class AnnouncementAdminViewSet(mixins.ListModelMixin,
                               mixins.CreateModelMixin,
                               mixins.UpdateModelMixin,
                               mixins.RetrieveModelMixin,
                               mixins.DestroyModelMixin,
                               viewsets.GenericViewSet):
    '''
    '''

    model = Announcement
    permission_classes = [Or(IsAdmin, IsStaff)]
    serializer_class = AnnouncementAdminSerializer
    queryset = Announcement.objects.all().order_by('-created_at', 'rank')
    filter_class = AnnouncementFilter
    renderer_classes = [GrizzlyRenderer]

    def destroy(self, request, pk):
        '''
        '''

        ret = super(AnnouncementAdminViewSet, self).destroy(request, pk)

        # update rank of remaining item
        announcements = Announcement.objects.all().order_by('rank')
        rank = 1
        for announcement in announcements:
            announcement.rank = rank
            rank += 1
            announcement.save()
        return ret


class AnnouncementMemberViewSet(mixins.ListModelMixin, viewsets.GenericViewSet,
                                mixins.RetrieveModelMixin):
    '''
    '''

    model = Announcement
    permission_classes = []
    serializer_class = AnnouncementMemberSerializer
    queryset = Announcement.objects.filter(status=1). \
        order_by('-created_at', 'rank')
    filter_class = AnnouncementFilter
    renderer_classes = [GrizzlyRenderer]


class PromotionClaimAdminViewset(mixins.ListModelMixin,
                                 mixins.CreateModelMixin,
                                 mixins.UpdateModelMixin,
                                 mixins.RetrieveModelMixin,
                                 mixins.DestroyModelMixin,
                                 viewsets.GenericViewSet):
    model = PromotionClaim
    permission_classes = [Or(IsAdmin, IsStaff)]
    queryset = PromotionClaim.objects.all().order_by('-created_at')
    serializer_class = PromotionClaimAdminSerializer
    filter_class = PromotionClaimFilter
    renderer_classes = [GrizzlyRenderer]


class PromotionClaimMemberViewset(mixins.CreateModelMixin,
                                  mixins.ListModelMixin,
                                  viewsets.GenericViewSet):
    model = PromotionClaim
    permission_classes = []
    queryset = PromotionClaim.objects.all().order_by('-created_at')
    serializer_class = PromotionClaimMemberSerializer
    renderer_classes = [GrizzlyRenderer]

    def get_queryset(self):
        username = self.request.GET.get('username')
        promotion_id = self.request.GET.get('promotion_id')

        params = {'username': username}
        if not username and promotion_id:  # username and promotion_id required
            return PromotionClaim.objects.none()

        if promotion_id != '0':
            params.update(promotion_id=promotion_id)

        return PromotionClaim.objects.filter(**params)
