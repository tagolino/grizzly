from django.conf.urls import url, include
from ticket import views as tickets
from rest_framework import routers


manage_router = routers.DefaultRouter()
manage_router.register(r'tickets',
                       tickets.TicketAdminViewset,
                       base_name='customer_tickets')

member_router = routers.DefaultRouter()
member_router.register(r'tickets',
                       tickets.TicketMemberViewset,
                       base_name='member_tickets')

urlpatterns = [
    url(r'^manage/', include(manage_router.urls)),
    url(r'^member/', include(member_router.urls)),
]
