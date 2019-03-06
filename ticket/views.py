from rest_condition import Or
from rest_framework import mixins, viewsets

from ticket.models import Ticket
from ticket.filters import TicketFilter
from ticket.serializers import (TicketAdminSerializer,
                                TicketMemberSerializer)
from grizzly.utils import GrizzlyRenderer
from loginsvc.permissions import IsAdmin, IsStaff


class TicketAdminViewset(mixins.ListModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.RetrieveModelMixin,
                         viewsets.GenericViewSet):
    model = Ticket
    permission_classes = [Or(IsAdmin, IsStaff)]
    queryset = Ticket.objects.all().order_by('-created_at')
    serializer_class = TicketAdminSerializer
    filter_class = TicketFilter
    renderer_classes = [GrizzlyRenderer]


class TicketMemberViewset(mixins.CreateModelMixin,
                          mixins.ListModelMixin,
                          viewsets.GenericViewSet):
    model = Ticket
    permission_classes = []
    queryset = Ticket.objects.all().order_by('-created_at')
    serializer_class = TicketMemberSerializer
    filter_class = TicketFilter
    renderer_classes = [GrizzlyRenderer]

    def get_queryset(self):
        username = self.request.GET.get('username')
        if not username:  # username required
            return Ticket.objects.none()

        return self.queryset.filter(username=username)
