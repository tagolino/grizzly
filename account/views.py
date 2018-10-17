import logging
import re

from django.contrib.auth import authenticate
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from rest_condition import Or
from rest_framework import mixins, viewsets
from rest_framework.decorators import (api_view,
                                       permission_classes)
from rest_framework.response import Response

from account.models import Staff
from account.serializers import StaffSerializer
from grizzly.utils import (parse_request_for_token,
                           get_user_type,
                           get_valid_token,
                           get_request_data,
                           GrizzlyRenderer)
from grizzly.lib import constants
from loginsvc.permissions import IsAdmin, IsStaff
from loginsvc.views import generate_response, force_logout


logger = logging.getLogger(__name__)


class StaffViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin,
                   mixins.CreateModelMixin, mixins.UpdateModelMixin,
                   mixins.DestroyModelMixin, viewsets.GenericViewSet):
    model = Staff
    permission_classes = [Or(IsStaff, IsAdmin)]
    queryset = Staff.objects.all()
    serializer_class = StaffSerializer
    renderer_classes = [GrizzlyRenderer]


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsStaff])
def reset_password(request):
    data = get_request_data(request)
    if request.method == 'POST':
        token_obj = get_valid_token(request)

        if token_obj:
            username = token_obj.user.username

            prev_password = data.get('prev_password')
            new_password = data.get('new_password')
            repeat_password = data.get('repeat_password')

            if repeat_password != new_password:
                return generate_response(constants.FIELD_ERROR,
                                         _('Passwords didn\'t matched'))

            pattern = re.compile('^[a-zA-Z0-9]{6,15}$')
            if not pattern.match(new_password):
                msg = _('Password must be 6 to 15 alphanumeric characters')
                return generate_response(constants.FIELD_ERROR, msg)

            user = authenticate(username=username, password=prev_password)
            if not user:
                return generate_response(constants.FIELD_ERROR,
                                         _('Incorrect previous password'))

            user.set_password(new_password)
            user.save()

            force_logout(user)

            return generate_response(constants.ALL_OK)

    return generate_response(constants.NOT_ALLOWED, _('Not Allowed'))


@csrf_exempt
@api_view(['GET'])
def current_user(request):
    user, user_grp = parse_request_for_token(request)
    if not user:
        return Response(data=constants.NOT_OK, status=404)
    return Response({'username': user.username,
                     'type': get_user_type(user)},
                    status=200)
