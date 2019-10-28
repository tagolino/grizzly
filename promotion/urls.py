from django.conf.urls import url, include
from promotion import views as promote
from rest_framework import routers


manage_router = routers.DefaultRouter()
manage_router.register(r'announcement',
                       promote.AnnouncementAdminViewSet,
                       base_name='announcements')
manage_router.register(r'promotions',
                       promote.PromotionAdminViewSet,
                       base_name='promotions')
manage_router.register(r'promo_items',
                       promote.PromotionElementAdminViewSet,
                       base_name='promotionelements')
manage_router.register(r'promotionclaim',
                       promote.PromotionClaimAdminViewset,
                       base_name='promotionsclaim')
manage_router.register(r'promotionbets/monthly',
                       promote.PromotionBetMonthlyAdminViewset,
                       base_name='promotionbets_monthly')
manage_router.register(r'promotionbets',
                       promote.PromotionBetAdminViewset,
                       base_name='promotionbets')
manage_router.register(r'promotionbetlevels',
                       promote.PromotionBetLevelAdminViewset,
                       base_name='promotionbetlevels')
manage_router.register(r'summary',
                       promote.SummaryAdminViewset,
                       base_name='promotionbetsummary')
manage_router.register(r'promotion/requestlog',
                       promote.ImportExportLogAdminViewset,
                       base_name='promotion_importexportlog')

member_router = routers.DefaultRouter()
member_router.register(r'announcement',
                       promote.AnnouncementMemberViewSet,
                       base_name='member_announcement')
member_router.register(r'promotion',
                       promote.PromotionMemberViewset),
member_router.register(r'promotionclaim',
                       promote.PromotionClaimMemberViewset,
                       base_name='member_promotionsclaim')
member_router.register(r'claim_count',
                       promote.DummyThrottleAPI,
                       base_name='dummy_api')
member_router.register(r'promotionbets/monthly',
                       promote.PromotionBetMonthlyViewset,
                       base_name='member_promotionbets_monthly')
member_router.register(r'promotionbets',
                       promote.PromotionBetViewset,
                       base_name='member_promotionbets')
member_router.register(r'promotionbetlevels',
                       promote.PromotionBetLevelViewset,
                       base_name='member_promotionbetlevels')
member_router.register(r'summary',
                       promote.SummaryViewset,
                       base_name='promotionbetsummary')

urlpatterns = [
    url(r'^manage/promotion/import/',
        promote.import_file, name='promotion_import'),
    url(r'^manage/', include(manage_router.urls)),
    url(r'^member/', include(member_router.urls)),
]
