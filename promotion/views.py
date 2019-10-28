import math

from datetime import timedelta
from django.core.cache import cache
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from rest_condition import Or
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.decorators import (action,
                                       api_view,
                                       renderer_classes)
from rest_framework.response import Response
from rest_framework.settings import api_settings
from tablib import Dataset
from time import time

from configsetting.models import GlobalPreference
from grizzly.lib import constants
from grizzly.throttling import CustomAnonThrottle
from grizzly.utils import (parse_request_for_token,
                           GrizzlyRenderer)
from loginsvc.permissions import IsAdmin, IsStaff
from loginsvc.views import generate_response
from promotion.filters import (AnnouncementFilter,
                               PromotionFilter,
                               PromotionBetFilter,
                               PromotionBetLevelFilter,
                               PromotionBetMonthlyFilter,
                               PromotionClaimFilter,
                               PromotionElementFilter,
                               ImportExportLogFilter,
                               SummaryFilter)
from promotion.models import (Announcement,
                              EGAMES_DEPOSIT_IMPORT,
                              LIVE_DEPOSIT_IMPORT,
                              GAME_TYPE_ELECTRONICS,
                              GAME_TYPE_LIVE,
                              Promotion,
                              PromotionElement,
                              PromotionClaim,
                              PromotionBet,
                              PromotionBetLevel,
                              PromotionBetMonthly,
                              REQUEST_LOG_DELETED,
                              ImportExportLog,
                              Summary)
from promotion.serializers import (AnnouncementAdminSerializer,
                                   AnnouncementMemberSerializer,
                                   PromotionAdminSerializer,
                                   PromotionMemberSerializer,
                                   PromotionElementAdminSerializer,
                                   PromotionElementMemberSerializer,
                                   PromotionBetAdminSerializer,
                                   PromotionBetMonthlyAdminSerializer,
                                   PromotionBetSerializer,
                                   PromotionBetLevelAdminSerializer,
                                   PromotionBetLevelSerializer,
                                   PromotionBetMonthlySerializer,
                                   PromotionClaimAdminSerializer,
                                   PromotionClaimMemberSerializer,
                                   ImportExportLogAdminSerializer,
                                   SummaryAdminSerializer,
                                   SummarySerializer)
from promotion.tasks import (cancel_request,
                             delete_request,
                             promotion_bet_import,
                             revert_bets,
                             update_member_bet_details,)


class AnnouncementAdminViewSet(mixins.ListModelMixin,
                               mixins.CreateModelMixin,
                               mixins.UpdateModelMixin,
                               mixins.RetrieveModelMixin,
                               mixins.DestroyModelMixin,
                               viewsets.GenericViewSet):
    model = Announcement
    permission_classes = [Or(IsAdmin, IsStaff)]
    serializer_class = AnnouncementAdminSerializer
    queryset = Announcement.objects.all().order_by('-created_at', 'rank')
    filter_class = AnnouncementFilter
    renderer_classes = [GrizzlyRenderer]

    def destroy(self, request, pk):
        ret = super(AnnouncementAdminViewSet, self).destroy(request, pk)

        # update rank of remaining item
        announcements = Announcement.objects.all().order_by('rank')
        rank = 1
        for announcement in announcements:
            announcement.rank = rank
            rank += 1
            announcement.save()
        return ret


class AnnouncementMemberViewSet(mixins.ListModelMixin, viewsets.GenericViewSet,
                                mixins.RetrieveModelMixin):
    model = Announcement
    permission_classes = []
    serializer_class = AnnouncementMemberSerializer
    queryset = Announcement.objects.filter(status=1). \
        order_by('-created_at', 'rank')
    filter_class = AnnouncementFilter
    renderer_classes = [GrizzlyRenderer]


class PromotionAdminViewSet(mixins.RetrieveModelMixin,
                            mixins.CreateModelMixin,
                            mixins.ListModelMixin,
                            mixins.UpdateModelMixin,
                            viewsets.GenericViewSet):
    model = Promotion
    queryset = model.objects.all().order_by('rank')
    permission_classes = [Or(IsAdmin, IsStaff)]
    serializer_class = PromotionAdminSerializer
    filter_class = PromotionFilter
    renderer_classes = [GrizzlyRenderer]

    def create(self, request):
        if request.GET.get('update_ranks'):
            try:
                pks = []
                dicts = {}
                for d in request.data:
                    pks.append(int(d.get('id')))
                    dicts[int(d.get('id'))] = d.get('rank')
                promotions = Promotion.objects.filter(pk__in=pks)
                for promotion in promotions:
                    promotion.rank = dicts.get(promotion.id)
                    promotion.save()
            except Exception:
                return Response({'msg': 'Unknown Error'})

            return Response({'msg': 'success'})

        return super().create(request)


class PromotionElementAdminViewSet(mixins.RetrieveModelMixin,
                                   mixins.CreateModelMixin,
                                   mixins.ListModelMixin,
                                   mixins.UpdateModelMixin,
                                   mixins.DestroyModelMixin,
                                   viewsets.GenericViewSet):
    model = PromotionElement
    queryset = model.objects.all()
    permission_classes = [Or(IsAdmin, IsStaff)]
    serializer_class = PromotionElementAdminSerializer
    filter_class = PromotionElementFilter
    renderer_classes = [GrizzlyRenderer]

    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get('data', {}), list):
            kwargs['many'] = True
        return super().get_serializer(*args, **kwargs)

    def create(self, request):
        if request.GET.get('update_ranks'):
            try:
                pks = []
                dicts = {}
                for d in request.data:
                    pks.append(int(d.get('id')))
                    dicts[int(d.get('id'))] = d.get('rank')
                promo_items = PromotionElement.objects.filter(pk__in=pks)
                for promo_item in promo_items:
                    promo_item.rank = dicts.get(promo_item.id)
                    promo_item.save()
            except Exception:
                return Response({'msg': 'Unknown Error'})

            return Response({'msg': 'success'})

        return super().create(request)


class PromotionMemberViewset(mixins.ListModelMixin,
                             mixins.RetrieveModelMixin,
                             viewsets.GenericViewSet):
    model = Promotion
    permission_classes = []
    queryset = Promotion.objects.filter(status=1).order_by('rank')
    serializer_class = PromotionMemberSerializer
    renderer_classes = [GrizzlyRenderer]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == 'list':
            context.update({'list': True})

        return context


class PromotionClaimAdminViewset(mixins.ListModelMixin,
                                 mixins.CreateModelMixin,
                                 mixins.UpdateModelMixin,
                                 mixins.RetrieveModelMixin,
                                 mixins.DestroyModelMixin,
                                 viewsets.GenericViewSet):
    model = PromotionClaim
    permission_classes = [Or(IsAdmin, IsStaff)]
    queryset = PromotionClaim.objects.all().order_by('-created_at')
    serializer_class = PromotionClaimAdminSerializer
    filter_class = PromotionClaimFilter
    renderer_classes = [GrizzlyRenderer]


class PromotionClaimMemberViewset(mixins.CreateModelMixin,
                                  mixins.ListModelMixin,
                                  viewsets.GenericViewSet):
    model = PromotionClaim
    permission_classes = []
    queryset = PromotionClaim.objects.all().order_by('-created_at')
    serializer_class = PromotionClaimMemberSerializer
    renderer_classes = [GrizzlyRenderer]
    throttle_classes = (CustomAnonThrottle,)

    def get_queryset(self):
        username = self.request.GET.get('username')
        promotion_id = self.request.GET.get('promotion_id')

        params = {'username': username}
        if not username and promotion_id:  # username and promotion_id required
            return PromotionClaim.objects.none()

        if promotion_id != '0':
            params.update(promotion_id=promotion_id)

        return PromotionClaim.objects.filter(**params)


class PromotionBetLevelAdminViewset(mixins.ListModelMixin,
                                    mixins.CreateModelMixin,
                                    mixins.UpdateModelMixin,
                                    mixins.RetrieveModelMixin,
                                    mixins.DestroyModelMixin,
                                    viewsets.GenericViewSet):
    model = PromotionBetLevel
    permission_classes = [Or(IsAdmin, IsStaff)]
    queryset = PromotionBetLevel.objects.all().order_by('total_bet')
    serializer_class = PromotionBetLevelAdminSerializer
    filter_class = PromotionBetLevelFilter
    renderer_classes = [GrizzlyRenderer]


class PromotionBetAdminViewset(mixins.ListModelMixin,
                               mixins.CreateModelMixin,
                               mixins.UpdateModelMixin,
                               mixins.RetrieveModelMixin,
                               mixins.DestroyModelMixin,
                               viewsets.GenericViewSet):
    model = PromotionBet
    permission_classes = [Or(IsAdmin, IsStaff)]
    queryset = PromotionBet.objects.all().order_by('-created_at')
    filter_class = PromotionBetFilter
    serializer_class = PromotionBetAdminSerializer
    renderer_classes = [GrizzlyRenderer]

    def destroy(self, request, pk):
        instance = self.get_object()
        user, user_grp = parse_request_for_token(request)

        update_member_bet_details(instance, user)

        instance.active = False
        instance.save()

        return generate_response(constants.ALL_OK)

    @action(detail=False, methods=['put'])
    def revert(self, request):
        bet_ids = request.POST.get('bet_ids', '')
        user, user_grp = parse_request_for_token(request)

        bets = PromotionBet.objects.filter(
            id__in=[int(bet_id) if bet_id else 0
                    for bet_id in bet_ids.split(',')],
            active=True)

        revert_bets.apply_async(
            (list(bets.values_list('id', flat=True)), user.id,),
            queue='bet_operations')

        bets.update(active=False)

        return generate_response(constants.ALL_OK)


class PromotionBetMonthlyAdminViewset(mixins.ListModelMixin,
                                      mixins.RetrieveModelMixin,
                                      viewsets.GenericViewSet):
    model = PromotionBetMonthly
    permission_classes = [Or(IsAdmin, IsStaff)]
    queryset = PromotionBetMonthly.objects.all().order_by('-cycle_begin')
    filter_class = PromotionBetMonthlyFilter
    serializer_class = PromotionBetMonthlyAdminSerializer
    renderer_classes = [GrizzlyRenderer]


class PromotionBetViewset(mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          viewsets.GenericViewSet):
    model = PromotionBet
    permission_classes = []
    queryset = PromotionBet.objects.filter(active=True).order_by('-created_at')
    filter_class = PromotionBetFilter
    serializer_class = PromotionBetSerializer
    renderer_classes = [GrizzlyRenderer]

    def list(self, request):
        game_type = request.GET.get('game_type', 0)
        username = request.GET.get('username', '')
        max_day_diff = GlobalPreference.objects.get_value(
            'max_no_bet_days')

        bets = PromotionBet.objects.filter(game_type=int(game_type),
                                           member__username=username) \
                                   .order_by('created_at')
        if bets.exists():
            last_bet = bets.last()
            date_last_bet = timezone.localtime(last_bet.created_at)
            today = timezone.localtime(timezone.now())

            date_diff = today - date_last_bet

            if date_diff.days > int(max_day_diff):
                return generate_response(constants.ALL_OK,
                                         _('一个月内没有投注的用户，将无法领取彩金'))

        return super().list(request)


class PromotionBetMonthlyViewset(mixins.ListModelMixin,
                                 mixins.RetrieveModelMixin,
                                 viewsets.GenericViewSet):
    model = PromotionBetMonthly
    permission_classes = []
    queryset = PromotionBetMonthly.objects.all().order_by('-id')
    filter_class = PromotionBetMonthlyFilter
    serializer_class = PromotionBetMonthlySerializer
    renderer_classes = [GrizzlyRenderer]

    def list(self, request):
        game_type = request.GET.get('game_type', 0)
        username = request.GET.get('username', '')
        max_day_diff = GlobalPreference.objects.get_value(
            'max_no_bet_days')

        bets = PromotionBet.objects.filter(game_type=int(game_type),
                                           member__username=username) \
                                   .order_by('created_at')
        if bets.exists():
            last_bet = bets.last()
            date_last_bet = timezone.localtime(last_bet.created_at)
            today = timezone.localtime(timezone.now())

            date_diff = today - date_last_bet

            if date_diff.days > int(max_day_diff):
                return generate_response(constants.ALL_OK,
                                         _('一个月内没有投注的用户，将无法领取彩金'))

        return super().list(request)


class PromotionBetLevelViewset(mixins.ListModelMixin,
                               mixins.RetrieveModelMixin,
                               viewsets.GenericViewSet):
    model = PromotionBetLevel
    permission_classes = []
    queryset = PromotionBetLevel.objects.all().order_by('total_bet')
    filter_class = PromotionBetLevelFilter
    serializer_class = PromotionBetLevelSerializer
    renderer_classes = [GrizzlyRenderer]


class SummaryAdminViewset(mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          viewsets.GenericViewSet):
    model = Summary
    permission_classes = [Or(IsAdmin, IsStaff)]
    queryset = Summary.objects.all().order_by('member__username')
    filter_class = SummaryFilter
    serializer_class = SummaryAdminSerializer
    renderer_classes = [GrizzlyRenderer]


class SummaryViewset(mixins.RetrieveModelMixin,
                     mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    model = Summary
    permission_classes = []
    queryset = Summary.objects.all()
    serializer_class = SummarySerializer
    filter_class = SummaryFilter
    renderer_classes = [GrizzlyRenderer]

    def list(self, request):
        game_type = request.GET.get('game_type', 0)
        username = request.GET.get('username', '')
        max_day_diff = GlobalPreference.objects.get_value(
            'max_no_bet_days')

        bets = PromotionBet.objects.filter(game_type=int(game_type),
                                           member__username=username) \
                                   .order_by('created_at')
        if bets.exists():
            last_bet = bets.last()
            date_last_bet = timezone.localtime(last_bet.created_at)
            today = timezone.localtime(timezone.now())

            date_diff = today - date_last_bet

            if date_diff.days > int(max_day_diff):
                return generate_response(constants.ALL_OK,
                                         _('一个月内没有投注的用户，将无法领取彩金'))

        return super().list(request)


class DummyThrottleAPI(viewsets.GenericViewSet):
    model = PromotionClaim
    permission_classes = []
    serializer_class = None
    renderer_classes = [GrizzlyRenderer]

    def wait_time(self, history, duration, num_requests, time_now):
        """
        Returns the recommended next request time in seconds.
        """
        if history:
            remaining_duration = duration - (time_now - history[-1])
        else:
            remaining_duration = duration

        available_requests = num_requests - len(history) + 1
        if available_requests <= 0:
            return None

        return remaining_duration / float(available_requests)

    def list(self, request, *args, **kwargs):
        username = request.GET.get('username')
        promotion = request.GET.get('promotion')
        time_now = time()
        claim_viewname = 'anonPromotionClaimMemberViewset'
        cache_key_fmt = f'throttle_{claim_viewname}_{username}_{promotion}'
        history = cache.get(cache_key_fmt, []).copy()
        throttle_class = CustomAnonThrottle()
        duration = throttle_class.duration
        num_requests = throttle_class.num_requests
        while history and history[-1] <= time_now - duration:
            history.pop()
        if len(history) >= num_requests:
            wait_time = self.wait_time(
                history, duration, num_requests, time_now)
            wait_time = math.ceil(wait_time or 0)
            wait_msg = f'Try in {wait_time} seconds'
            return Response(
                {constants.ACTION_TOO_FREQUENT: wait_msg}, status=400)
        return Response()


class ImportExportLogAdminViewset(mixins.CreateModelMixin,
                                  mixins.ListModelMixin,
                                  mixins.RetrieveModelMixin,
                                  mixins.UpdateModelMixin,
                                  mixins.DestroyModelMixin,
                                  viewsets.GenericViewSet):
    model = ImportExportLog
    permission_classes = [Or(IsAdmin, IsStaff)]
    queryset = ImportExportLog.objects.all().order_by('-created_at')
    serializer_class = ImportExportLogAdminSerializer
    filter_class = ImportExportLogFilter
    renderer_classes = [GrizzlyRenderer]

    def destroy(self, request, pk):
        user, user_grp = parse_request_for_token(request)

        request_log = ImportExportLog.objects.get(id=pk)
        request_log.status = REQUEST_LOG_DELETED
        request_log.save(update_fields=['status'])

        delete_request.apply_async((pk, user.id,), queue='bet_operations')

        return generate_response(constants.ALL_OK)


@api_view(['POST'])
@renderer_classes((GrizzlyRenderer,))
@csrf_exempt
def import_file(request):
    user, user_grp = parse_request_for_token(request)
    if not user:
        return generate_response(constants.NOT_ALLOWED,
                                 _('Request not allowed'))

    import_type = request.GET.get('import_type')
    game_type = request.GET.get('game_type', GAME_TYPE_ELECTRONICS)
    request_type = EGAMES_DEPOSIT_IMPORT
    if int(game_type) == GAME_TYPE_ELECTRONICS:
        request_type = EGAMES_DEPOSIT_IMPORT
    elif int(game_type) == GAME_TYPE_LIVE:
        request_type = LIVE_DEPOSIT_IMPORT

    if import_type == 'promotion_bets':
        new_bets = request.FILES.get('import_file')
        if not new_bets:
            return generate_response(constants.FIELD_ERROR,
                                     msg=_('No incoming files'))

        file_name = new_bets.__str__()

        if file_name.endswith('.csv'):
            import_data = Dataset().load(new_bets.read().decode('utf-8'),
                                         format='csv')

        elif file_name.endswith('.xlsx') or file_name.endswith('.xls'):
            import_data = Dataset()
            import_data.xlsx = new_bets.read()

        else:
            return generate_response(constants.FIELD_ERROR,
                                     msg=_('Only supports csv and xlsx files'))

        if not {'username', 'amount'}.issubset(import_data.headers):
            return generate_response(constants.FIELD_ERROR,
                                     msg=_(f'Invalid file header format.'))

        request_log = ImportExportLog.objects.create(
            game_type=game_type,
            request_type=request_type,
            filename=file_name,
            created_by=user,
        )

        cancel_request.apply_async((request_log.id,),
                                   eta=timezone.now() + timedelta(minutes=60),
                                   queue='bet_operations')

        promotion_bet_import.apply_async((import_data.dict,
                                          user.id,
                                          int(game_type),
                                          request_log.id,),
                                         queue='bet_operations')

    else:
        return generate_response(constants.NOT_ALLOWED,
                                 msg=_('Request not allowed'))

    return generate_response(constants.ALL_OK,
                             data=import_data.dict)
