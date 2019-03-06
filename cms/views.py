import logging
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_condition import Or
from grizzly.utils import GrizzlyRenderer
from grizzly.lib import constants
from .models import Website, AdPage, Advertisement
from loginsvc.permissions import IsAdmin, IsStaff
from .serializers import (
    WebsiteSerializer,
    AdPageSerializer,
    AdvertisementSerializer,
    AdMemberPageSerializer
)


logger = logging.getLogger(__name__)


class WebsiteViewSet(mixins.RetrieveModelMixin,
                     mixins.CreateModelMixin,
                     mixins.ListModelMixin,
                     mixins.UpdateModelMixin,
                     viewsets.GenericViewSet):
    model = Website
    queryset = model.objects.all()
    permission_classes = [Or(IsAdmin, IsStaff)]
    serializer_class = WebsiteSerializer
    renderer_classes = [GrizzlyRenderer]


class AdPageViewSet(mixins.RetrieveModelMixin,
                    mixins.CreateModelMixin,
                    mixins.ListModelMixin,
                    mixins.UpdateModelMixin,
                    viewsets.GenericViewSet):
    model = AdPage
    queryset = model.objects.all()
    permission_classes = [Or(IsAdmin, IsStaff)]
    serializer_class = AdPageSerializer
    renderer_classes = [GrizzlyRenderer]


class AdvertisementViewSet(mixins.RetrieveModelMixin,
                           mixins.CreateModelMixin,
                           mixins.ListModelMixin,
                           mixins.UpdateModelMixin,
                           mixins.DestroyModelMixin,
                           viewsets.GenericViewSet):
    model = Advertisement
    queryset = model.objects.all()
    permission_classes = [Or(IsAdmin, IsStaff)]
    serializer_class = AdvertisementSerializer
    renderer_classes = [GrizzlyRenderer]


class PageMemberViewSet(mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    model = AdPage
    queryset = model.objects.all()
    permission_classes = []
    serializer_class = AdMemberPageSerializer
    # lookup_field = 'page'
    renderer_classes = [GrizzlyRenderer]


class AdsRankViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    model = Advertisement
    queryset = model.objects.all()
    permission_classes = [Or(IsAdmin, IsStaff)]
    renderer_classes = [GrizzlyRenderer]

    def create(self, request, *args, **kwargs):
        data = request.data
        if not isinstance(data, list):
            return Response(constants.NOT_OK, status=400)
        ads_list = []
        for item in data:
            try:
                s_rank = item.get('rank')
                ads = Advertisement.objects.get(id=item.get('id'))
                ads.rank = s_rank
                ads.save()
                ads_list.append(ads)
            except:
                # ignore error but current item will not be updated
                # no id, invalid keys, etc.
                pass
        serializer = AdvertisementSerializer(ads_list, many=True)
        return Response(data=serializer.data, status=200)
