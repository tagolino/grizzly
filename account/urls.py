from django.conf.urls import url, include
from account import views as account
from rest_framework import routers

manage_router = routers.DefaultRouter()
manage_router.register(r'staff',
                       account.StaffViewSet,
                       base_name='staff')
manage_router.register(r'member',
                       account.MemberAdminViewset,
                       base_name='member')

member_router = routers.DefaultRouter()
member_router.register(r'member',
                       account.MemberViewset,
                       base_name='member')
member_router.register(r'captcha',
                       account.CaptchaMemberViewSet,
                       base_name='member_captcha')

urlpatterns = [
    url(r'^manage/', include(manage_router.urls)),
    url(r'^member/', include(member_router.urls)),

    url(r'^manage/password/$', account.reset_password,
        name='dashboard_reset_password'),
    url(r'^manage/my/$', account.current_user, name='admin_current_user'),
]
