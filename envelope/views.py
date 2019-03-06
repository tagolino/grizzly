import logging
import random

from django.utils.translation import ugettext as _
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_condition import Or
from rest_framework import mixins, viewsets
from rest_framework.decorators import (api_view,
                                       renderer_classes)
from tablib import Dataset

from grizzly.lib import constants
from grizzly.utils import (parse_request_for_token,
                           GrizzlyRenderer)
from loginsvc.permissions import IsAdmin, IsStaff
from loginsvc.views import generate_response
from envelope.filters import (EnvelopeAmountSettingFilter,
                              EnvelopeClaimFilter,
                              EnvelopeDepositFilter,
                              EnvelopeLevelFilter)
from envelope.models import (EnvelopeLevel,
                             EnvelopeDeposit,
                             EnvelopeClaim,
                             EnvelopeAmountSetting,
                             ENVELOPE_TYPE_OPTIONS)
from envelope.serializers import (EnvelopeClaimMemberSerializer,
                                  EnvelopeClaimAdminSerializer,
                                  EnvelopeDepositAdminSerializer,
                                  EnvelopeLevelAdminSerializer,
                                  EnvelopeLevelMemberSerializer,
                                  EnvelopeSettingAdminSerializer)

from configsetting.models import GlobalPreference

from envelope.tasks import envelope_deposit_import

logger = logging.getLogger(__name__)


class EnvelopeClaimMemberViewset(mixins.CreateModelMixin,
                                 mixins.ListModelMixin,
                                 viewsets.GenericViewSet):
    model = EnvelopeClaim
    permission_classes = []
    queryset = EnvelopeClaim.objects.all().order_by('-created_at')
    serializer_class = EnvelopeClaimMemberSerializer
    filter_class = EnvelopeClaimFilter
    renderer_classes = [GrizzlyRenderer]

    def get_queryset(self):
        username = self.request.GET.get('username')

        params = {'username': username}
        if not username:  # username required
            return EnvelopeClaim.objects.none()

        return EnvelopeClaim.objects.filter(**params).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        envelope_type = int(request.GET.get('type', 0))
        envelope_type_desc = dict(ENVELOPE_TYPE_OPTIONS).get(
            envelope_type, 'envelope').lower()

        remaining_amount = EnvelopeClaim.objects.\
            remaining_pool_amount(envelope_type)
        if round(remaining_amount, 2) == 0:
            # No remaining pool
            return Response(constants.NO_POOL_AMOUNT_LEFT, status=400)

        username = request.data['username']
        # Get user claim left
        user_claim_left = EnvelopeClaim.objects.\
            get_quantity_left(username, envelope_type)
        if user_claim_left == 0:
            return Response(constants.NO_CLAIM_LEFT, status=400)

        data = {
            'username': username,
            'amount': 0,
            'status': 0,
            'envelope_type': envelope_type
        }

        threshold_range = EnvelopeClaim.objects.get_threshold_range(
            username, envelope_type)
        if threshold_range:
            claim_amount = round(
                random.uniform(float(threshold_range['min_amount']),
                               float(threshold_range['max_amount'])), 2)
        else:
            # Get random amount to claim
            claim_amount_from = GlobalPreference.objects.\
                get_value(f'{envelope_type_desc}_claim_amount_from')
            claim_amount_to = GlobalPreference.objects.\
                get_value(f'{envelope_type_desc}_claim_amount_to')

            claim_amount = round(random.uniform(
                float(claim_amount_from), float(claim_amount_to)), 2)

        if remaining_amount > claim_amount:
            data['amount'] = claim_amount
        else:
            # check if we can get remaining amount
            if remaining_amount > 0:
                data['amount'] = round(remaining_amount, 2)

        serializer = EnvelopeClaimMemberSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(data=serializer.data, status=200)

    def list(self, request, *args, **kwargs):
        if request.query_params.get('total'):
            data = self.get_queryset().filter(
                created_at__date=timezone.now().date(),
                status=1).aggregate(total=Sum('amount'))
            data['total'] = data.get('total', 0) or 0
            return Response(data)
        elif request.query_params.get('claim_left'):
            username = self.request.GET.get('username')
            envelope_type = request.GET.get('type', 0)

            claim_left = EnvelopeClaim.objects.get_quantity_left(
                username, envelope_type)

            return Response({'claim_left': claim_left})

        return super().list(args, kwargs)


class EnvelopeClaimAdminViewset(mixins.ListModelMixin,
                                mixins.CreateModelMixin,
                                mixins.UpdateModelMixin,
                                mixins.RetrieveModelMixin,
                                mixins.DestroyModelMixin,
                                viewsets.GenericViewSet):
    model = EnvelopeClaim
    permission_classes = [Or(IsAdmin, IsStaff)]
    queryset = EnvelopeClaim.objects.all().order_by('-created_at')
    serializer_class = EnvelopeClaimAdminSerializer
    filter_class = EnvelopeClaimFilter
    renderer_classes = [GrizzlyRenderer]

    @action(detail=False, methods=['put'])
    def approve_all(self, request):
        envelope_type = request.GET.get('type', 0)
        queryset = EnvelopeClaim.objects.filter(status=0,
                                                envelope_type=envelope_type)
        total_before_update = queryset.count()
        total_after_update = queryset.update(status=1)

        logger.info(f'Queried pending EnvelopeClaim count: \
            {total_before_update}')
        logger.info(f'Updated query count: {total_after_update}')

        # Note: Possible scaling options (celery)

        return Response(data=[{'total': total_after_update}], status=200)


class EnvelopeDepositAdminViewset(mixins.ListModelMixin,
                                  mixins.CreateModelMixin,
                                  mixins.UpdateModelMixin,
                                  mixins.RetrieveModelMixin,
                                  mixins.DestroyModelMixin,
                                  viewsets.GenericViewSet):
    model = EnvelopeDeposit
    permission_classes = [Or(IsAdmin, IsStaff)]
    queryset = EnvelopeDeposit.objects.all().order_by('-created_at')
    serializer_class = EnvelopeDepositAdminSerializer
    filter_class = EnvelopeDepositFilter
    renderer_classes = [GrizzlyRenderer]


class EnvelopeLevelAdminViewset(mixins.ListModelMixin,
                                mixins.CreateModelMixin,
                                mixins.UpdateModelMixin,
                                mixins.RetrieveModelMixin,
                                mixins.DestroyModelMixin,
                                viewsets.GenericViewSet):
    model = EnvelopeLevel
    permission_classes = [Or(IsAdmin, IsStaff)]
    queryset = EnvelopeLevel.objects.all().order_by('amount')
    serializer_class = EnvelopeLevelAdminSerializer
    filter_class = EnvelopeLevelFilter
    renderer_classes = [GrizzlyRenderer]


class EnvelopeLevelMemberViewset(mixins.ListModelMixin,
                                 viewsets.GenericViewSet):
    model = EnvelopeLevel
    permission_classes = []
    queryset = EnvelopeLevel.objects.all().order_by('amount')
    serializer_class = EnvelopeLevelMemberSerializer
    filter_class = EnvelopeLevelFilter
    renderer_classes = [GrizzlyRenderer]


class EnvelopeSettingAdminViewset(mixins.ListModelMixin,
                                  mixins.CreateModelMixin,
                                  mixins.UpdateModelMixin,
                                  mixins.RetrieveModelMixin,
                                  mixins.DestroyModelMixin,
                                  viewsets.GenericViewSet):
    model = EnvelopeAmountSetting
    permission_classes = [Or(IsAdmin, IsStaff)]
    queryset = EnvelopeAmountSetting.objects.all()
    serializer_class = EnvelopeSettingAdminSerializer
    filter_class = EnvelopeAmountSettingFilter
    renderer_classes = [GrizzlyRenderer]


@api_view(['POST'])
@renderer_classes((GrizzlyRenderer,))
@csrf_exempt
def import_file(request):
    user, user_grp = parse_request_for_token(request)
    if not user:
        return generate_response(constants.NOT_ALLOWED,
                                 _('Request not allowed'))

    import_type = request.GET.get('import_type')

    if import_type == 'envelope_deposit':
        deposits = request.FILES.get('import_file')
        envelope_type = request.GET.get('type', 0)

        if not deposits:
            return generate_response(constants.NOT_ALLOWED,
                                     msg=_('No incoming files'))

        file_name = deposits.__str__()

        if file_name.endswith('.csv'):
            import_data = Dataset().load(deposits.read().decode('utf-8'),
                                         format='csv')

        elif file_name.endswith('.xlsx') or file_name.endswith('.xls'):
            import_data = Dataset()
            import_data.xlsx = deposits.read()

        else:
            return generate_response(constants.FIELD_ERROR,
                                     msg=_('Only supports csv and xlsx files'))

        envelope_deposit_import.apply_async((import_data.dict,
                                             user.id,
                                             envelope_type),
                                            queue='envelope_operations')

    else:
        return generate_response(constants.NOT_ALLOWED,
                                 msg=_('Request not allowed'))

    return generate_response(constants.ALL_OK,
                             data=import_data.dict)
