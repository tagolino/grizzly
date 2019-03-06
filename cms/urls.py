from django.conf.urls import url, include
from .import views as cms
from rest_framework import routers


router = routers.DefaultRouter()
router.register(r'website', cms.WebsiteViewSet,
                base_name='cms_website')
router.register(r'ads_page', cms.AdPageViewSet,
                base_name='ads_page')
router.register(r'advertisement', cms.AdvertisementViewSet,
                base_name='ads')
router.register(r'ads_rank', cms.AdsRankViewSet,
                base_name='ads_rank')

member_router = routers.DefaultRouter()
member_router.register(r'ads',
                       cms.PageMemberViewSet,
                       base_name='ads_page_member')

urlpatterns = [
    url(r'^manage/', include(router.urls)),
    url(r'^member/', include(member_router.urls))
]
