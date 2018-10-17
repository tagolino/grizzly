from django.conf.urls import url, include
from promotion import views as promote
from rest_framework import routers


manage_router = routers.DefaultRouter()
manage_router.register(r'announcement',
                       promote.AnnouncementAdminViewSet,
                       base_name='announcements')
manage_router.register(r'promotionclaim',
                       promote.PromotionClaimAdminViewset,
                       base_name='promotionsclaim')

member_router = routers.DefaultRouter()
member_router.register(r'announcement',
                       promote.AnnouncementMemberViewSet,
                       base_name='member_announcement')
member_router.register(r'promotionclaim',
                       promote.PromotionClaimMemberViewset,
                       base_name='member_promotionsclaim')

urlpatterns = [
    url(r'^manage/', include(manage_router.urls)),
    url(r'^member/', include(member_router.urls)),
]
