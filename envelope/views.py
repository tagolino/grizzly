import logging

from datetime import timedelta
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
                              EnvelopeLevelFilter,
                              EventTypeFilter,
                              RequestLogFilter,
                              RewardFilter)
from envelope.models import (EnvelopeLevel,
                             EnvelopeDeposit,
                             EnvelopeClaim,
                             EnvelopeAmountSetting,
                             EventType,
                             RequestLog,
                             TYPE_ENVELOPE_DEPOSIT_IMPORT,
                             Reward,
                             TYPE_WHEEL)
from envelope.serializers import (EnvelopeClaimMemberSerializer,
                                  EnvelopeClaimAdminSerializer,
                                  EnvelopeDepositAdminSerializer,
                                  EnvelopeDepositMemberSerializer,
                                  EnvelopeLevelAdminSerializer,
                                  EnvelopeLevelMemberSerializer,
                                  EnvelopeSettingAdminSerializer,
                                  EventTypeAdminSerializer,
                                  EventTypeMemberSerializer,
                                  RequestLogAdminSerializer,
                                  RewardAdminSerializer,
                                  RewardMemberSerializer)

from configsetting.models import GlobalPreference

from envelope.tasks import (envelope_deposit_import,
                            cancel_request,)


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
        username = request.data.get('username', '')

        event_type = EnvelopeClaim.objects.get_event_type(
            request.data.get('event_type', 0))
        if not event_type:
            return Response(constants.INVALID_EVENT_TYPE, status=400)

        # Get user claim left
        user_claim_left = EnvelopeClaim.objects.get_quantity_left(
            username, event_type)
        if user_claim_left is None:
            return Response(constants.CANNOT_CLAIM_YET, status=400)
        elif user_claim_left == 0:
            return Response(constants.NO_CLAIM_LEFT, status=400)

        data = {
            'username': username,
            'amount': 0.0,
            'status': 0,
            'event_type': event_type.id
        }

        if event_type.is_reward:
            reward = EnvelopeClaim.objects.get_reward(event_type)

            data.update(reward=reward.id)
        else:
            remaining_amount = EnvelopeClaim.objects.remaining_pool_amount(
                event_type)
            if round(remaining_amount, 2) <= 0:
                # No remaining pool
                return Response(constants.NO_POOL_AMOUNT_LEFT, status=400)

            amount_threshold = EnvelopeClaim.objects.get_threshold_range(
                username, event_type)

            if amount_threshold[0] == amount_threshold[1]:
                return Response(constants.CANNOT_CLAIM_YET, status=400)

            claim_amount = EnvelopeClaim.objects.get_claim_amount(
                event_type, amount_threshold)

            if remaining_amount > claim_amount:
                data.update(amount=claim_amount)
            else:
                if remaining_amount > 0:
                    data.update(amount=round(remaining_amount, 2))

        serializer = EnvelopeClaimMemberSerializer(
            data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(data=serializer.data, status=200)

    def list(self, request, *args, **kwargs):
        if request.query_params.get('total'):
            today = timezone.localtime(timezone.now()).date()
            event_type = EnvelopeClaim.objects.get_event_type(
                request.GET.get('event_type', 0))
            if not event_type:
                return Response(constants.INVALID_EVENT_TYPE, status=400)
            data = self.get_queryset().filter(created_at__date=today,
                                              status=1,
                                              event_type=event_type).\
                aggregate(total=Sum('amount'))
            data['total'] = data.get('total', 0) or 0
            return Response(data)
        elif request.query_params.get('claim_left'):
            username = self.request.GET.get('username', '')
            event_type = EnvelopeClaim.objects.get_event_type(
                request.GET.get('event_type', 0))
            if not event_type:
                return Response(constants.INVALID_EVENT_TYPE, status=400)

            claim_left = EnvelopeClaim.objects.get_quantity_left(
                username, event_type)

            if claim_left is None:
                return Response(constants.CANNOT_CLAIM_YET, status=400)

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
        event_type = EnvelopeClaim.objects.get_event_type(
            request.data.get('event_type', 0))
        if not event_type:
            return Response(constants.INVALID_EVENT_TYPE, status=400)

        queryset = EnvelopeClaim.objects.filter(
            status=0, event_type=event_type)

        total_before_update = queryset.count()
        total_after_update = 0

        for envelope_claim in queryset:
            try:
                envelope_claim.status = 1
                envelope_claim.memo = '点击通过所有'
                envelope_claim.updated_by = request.user
                envelope_claim.save()
                total_after_update += 1
            except Exception as e:
                logger.error('An error occured in the middle of all approval')
                logger.error(e)

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
                                  viewsets.GenericViewSet):
    model = EnvelopeAmountSetting
    permission_classes = [Or(IsAdmin, IsStaff)]
    queryset = EnvelopeAmountSetting.objects.all()
    serializer_class = EnvelopeSettingAdminSerializer
    filter_class = EnvelopeAmountSettingFilter
    renderer_classes = [GrizzlyRenderer]


class EnvelopeDepositMemberViewset(mixins.ListModelMixin,
                                   viewsets.GenericViewSet):
    model = EnvelopeDeposit
    permission_classes = []
    queryset = EnvelopeDeposit.objects.all().order_by('-created_at')
    serializer_class = EnvelopeDepositMemberSerializer
    filter_class = EnvelopeDepositFilter
    renderer_classes = [GrizzlyRenderer]

    def get_queryset(self):
        params = {}
        if not self.request.GET.get('username'):
            return EnvelopeDeposit.objects.none()
        else:
            params.update(username=self.request.GET.get('username'))

        if not self.request.GET.get('event_type'):
            return EnvelopeDeposit.objects.none()
        else:
            params.update(event_type__code=self.request.GET.get('event_type'))

        return self.queryset.filter(**params)

    def list(self, request, *args, **kwargs):
        event_type = EnvelopeClaim.objects.get_event_type(
            request.GET.get('event_type', 0))
        if not event_type:
            return Response(constants.INVALID_EVENT_TYPE, status=400)
        elif event_type.is_reward:
            qs = self.get_queryset().aggregate(Sum('amount'))
            data = {
                'username': request.GET.get('username'),
                'amount': qs.get('amount__sum') or 0
            }
            return Response(data=data, status=200)

        return super().list(args, kwargs)


class RewardAdminViewset(mixins.ListModelMixin,
                         mixins.CreateModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.RetrieveModelMixin,
                         viewsets.GenericViewSet):
    model = Reward
    permission_classes = [Or(IsAdmin, IsStaff)]
    queryset = Reward.objects.all().order_by('id')
    serializer_class = RewardAdminSerializer
    filter_class = RewardFilter
    renderer_classes = [GrizzlyRenderer]


class RewardMemberViewset(mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          viewsets.GenericViewSet):
    model = Reward
    permission_classes = []
    queryset = Reward.objects.all().order_by('id')
    serializer_class = RewardMemberSerializer
    filter_class = RewardFilter
    renderer_classes = [GrizzlyRenderer]


class EventTypeAdminViewset(mixins.ListModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            viewsets.GenericViewSet):
    model = EventType
    permission_classes = [Or(IsAdmin, IsStaff)]
    queryset = EventType.objects.all().order_by('id')
    serializer_class = EventTypeAdminSerializer
    filter_class = EventTypeFilter
    renderer_classes = [GrizzlyRenderer]


class EventTypeMemberViewset(mixins.ListModelMixin,
                             viewsets.GenericViewSet):
    model = EventType
    permission_classes = []
    queryset = EventType.objects.all()
    serializer_class = EventTypeMemberSerializer
    filter_class = EventTypeFilter
    renderer_classes = [GrizzlyRenderer]

    def get_queryset(self):
        params = {}
        if not self.request.GET.get('code'):
            return EventType.objects.none()
        else:
            params.update(code=self.request.GET.get('code'))

        return self.queryset.filter(**params)


class RequestLogAdminViewset(mixins.CreateModelMixin,
                             mixins.ListModelMixin,
                             mixins.RetrieveModelMixin,
                             mixins.UpdateModelMixin,
                             viewsets.GenericViewSet):
    model = RequestLog
    permission_classes = [Or(IsAdmin, IsStaff)]
    queryset = RequestLog.objects.all().order_by('-created_at')
    serializer_class = RequestLogAdminSerializer
    filter_class = RequestLogFilter
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
        event_type = EventType.objects.filter(
            code=request.data.get('event_type', ''))

        if not deposits:
            return generate_response(constants.NOT_ALLOWED,
                                     msg=_('No incoming files'))

        if not event_type.exists():
            return generate_response(constants.NOT_ALLOWED,
                                     msg=_('Invalid event type'))

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

        request_log = RequestLog.objects.create(
            event_type=event_type.first(),
            request_type=TYPE_ENVELOPE_DEPOSIT_IMPORT,
            filename=file_name,
            created_by=user,
        )

        cancel_request.apply_async((request_log.id,),
                                   eta=timezone.now() + timedelta(minutes=60),
                                   queue='envelope_operations')

        envelope_deposit_import.apply_async((import_data.dict,
                                             user.id,
                                             event_type.first().id,
                                             request_log.id),
                                            queue='envelope_operations')

    else:
        return generate_response(constants.NOT_ALLOWED,
                                 msg=_('Request not allowed'))

    return generate_response(constants.ALL_OK,
                             data=import_data.dict)
