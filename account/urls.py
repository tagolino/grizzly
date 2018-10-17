from django.conf.urls import url, include
from account import views as account
from rest_framework import routers

manage_router = routers.DefaultRouter()
manage_router.register(r'staff',
                       account.StaffViewSet,
                       base_name='staff')

urlpatterns = [
    url(r'^manage/', include(manage_router.urls)),
    url(r'^manage/password/$', account.reset_password,
        name='dashboard_reset_password'),
    url(r'^manage/my/$', account.current_user, name='admin_current_user'),
]
