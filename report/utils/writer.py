import csv
import logging
import os
import zipfile

from collections import OrderedDict
from datetime import datetime, timedelta
from django.http import HttpResponse
from django.utils import timezone
from django.utils.http import urlquote
from django.db.models import Sum
from io import BytesIO

from account.models import Member
from grizzly.utils import get_user_type
from oauth2_provider.models import AccessToken
from promotion.models import (EGAME_SUMMARY_EXPORT,
                              GAME_TYPE_ELECTRONICS,
                              GAME_TYPE_LIVE,
                              LIVE_SUMMARY_EXPORT,
                              PromotionBet,
                              PromotionClaim,
                              ImportExportLog,
                              REQUEST_LOG_COMPLETED,
                              REQUEST_LOG_CANCELED,
                              Summary)
from envelope.models import (EnvelopeClaim,
                             EventType)


logger = logging.getLogger(__name__)


STATUS_OPTIONS = (
    (0, '待审核'),
    (1, '通过'),
    (2, '驳回')
)


def parse_token_param(request):
    user = None
    user_type = None
    try:
        token = request.GET.get('token')
        token_obj = AccessToken.objects.filter(token=token).first()
        user = token_obj.user
        user_type = get_user_type(user)
    except Exception as exc:
        logger.info(exc)

    return user, user_type


class PromotionClaimReportWriter(object):

    def __init__(self, request):
        self.request = request
        self.status_options = dict(STATUS_OPTIONS)

    def get_queryset(self, data):
        filters = {}
        user, user_type = parse_token_param(self.request)
        if user_type not in {'staff', 'admin'}:
            return PromotionClaim.objects.none()

        if data.get('status'):
            filters.update(status=data.get('status'))

        start_date = data.get('created_at_after')
        end_date = data.get('created_at_before')
        if start_date and end_date:
            start_date = datetime.strptime(
                f'{start_date} 00:00:00', '%Y-%m-%d %H:%M:%S')

            end_date = datetime.strptime(
                f'{end_date} 23:59:59', '%Y-%m-%d %H:%M:%S')

            filters.update(created_at__range=(start_date, end_date))

        if data.get('username'):
            filters.update(username__contains=data.get('username'))

        if data.get('game_name'):
            filters.update(game_name__contains=data.get('game_name'))

        return PromotionClaim.objects.filter(**filters)

    def write_report(self):
        data = self.request.GET.copy()

        queryset = self.get_queryset(data)
        data = list(queryset.values(
            'username', 'game_name', 'created_at', 'updated_at',
            'claim_forms', 'status', 'updated_by__username', 'memo'
        ))

        return self.__write_report_file(data)

    def __write_report_file(self, data):
        filename = timezone.now().strftime('%Y%m%d')
        if not os.path.exists('temp_files'):  # create temp folder
            os.mkdir('temp_files')

        csv_file = f'temp_files/{filename}-统计报表.csv'

        # write to temporary csv file
        self.__write_to_csv(csv_file, data)

        # create zip file for the csv
        zipfile_temp = BytesIO()
        with zipfile.ZipFile(zipfile_temp, 'w') as zf:
            base_file = csv_file.split('/')[1]
            zf.write(csv_file, arcname=base_file)
        response = HttpResponse(content_type='application/zip')
        fname = f'{filename}-统计报表.zip'
        content_disposition = f'attachment; filename="{urlquote(fname)}"'
        response['Content-Disposition'] = content_disposition
        zipfile_temp.seek(0)
        response.write(zipfile_temp.read())

        # delete temporary csv file
        os.remove(csv_file)

        return response

    def __write_to_csv(self, csv_file, data):
        headers = self.__get_headers()

        with open(csv_file, 'w') as csvf:
            csv.writer(csvf).writerow(
                [s for s in headers.keys()])
            for d in data:
                username = d.get('username')
                game_name = d.get('game_name')
                created_at = d.get('created_at').strftime('%Y-%m-%d %H:%M:%S')
                updated_at = d.get('updated_at').strftime('%Y-%m-%d %H:%M:%S')
                claim_forms = []
                for form_key, form_value in d.get('claim_forms').items():
                    try:
                        if isinstance(form_value, list):
                            form_value = ', '.join(form_value)
                    except Exception as exc:
                        logger.error(exc)
                    claim_forms.append(f'{form_key}: {form_value}')
                claim_forms = '; '.join(claim_forms)
                status = self.status_options.get(d.get('status'))
                updated_by = d.get('updated_by__username', '')
                memo = d.get('memo', '')

                rows = [
                    username,
                    game_name,
                    created_at,
                    updated_at,
                    claim_forms,
                    status,
                    updated_by,
                    memo,
                ]

                csv.writer(csvf).writerow(rows)

    def __get_headers(self):
        csv_headers = {
            '会员账号': 'username',
            '活动名称': 'game_name',
            '创建时间': 'created_at',
            '更新时间': 'updated_at',
            '申请内容': 'claim_forms',
            '状态': 'status',
            '处理人员': 'updated_by',
            '备注': 'memo'
        }

        return csv_headers


class PromotionBetReportWriter(object):

    def __init__(self, request):
        self.request = request

    def get_queryset(self, data):
        filters = {}
        user, user_type = parse_token_param(self.request)
        if user_type not in {'staff', 'admin'}:
            return PromotionBet.objects.none()

        start_date = data.get('created_at_after')
        end_date = data.get('created_at_before')
        if start_date and end_date:
            start_date = datetime.strptime(
                f'{start_date} 00:00:00', '%Y-%m-%d %H:%M:%S')

            end_date = datetime.strptime(
                f'{end_date} 23:59:59', '%Y-%m-%d %H:%M:%S')

            filters.update(created_at__date__range=(start_date, end_date))

        if data.get('username'):
            filters.update(username__contains=data.get('username'))

        return PromotionBet.objects.filter(**filters)

    def write_report(self):
        data = self.request.GET.copy()

        queryset = self.get_queryset(data)
        data = list(queryset.values(
            'username', 'amount', 'promotion_bet_level__name',
            'created_at', 'memo',))

        return self.__write_report_file(data)

    def __write_report_file(self, data):
        filename = timezone.now().strftime('%Y%m%d')
        if not os.path.exists('temp_files'):  # create temp folder
            os.mkdir('temp_files')

        csv_file = f'temp_files/{filename}-晋级礼金.csv'

        # write to temporary csv file
        self.__write_to_csv(csv_file, data)

        # create zip file for the csv
        zipfile_temp = BytesIO()
        with zipfile.ZipFile(zipfile_temp, 'w') as zf:
            base_file = csv_file.split('/')[1]
            zf.write(csv_file, arcname=base_file)
        response = HttpResponse(content_type='application/zip')
        fname = f'{filename}-晋级礼金.zip'
        content_disposition = f'attachment; filename="{urlquote(fname)}"'
        response['Content-Disposition'] = content_disposition
        zipfile_temp.seek(0)
        response.write(zipfile_temp.read())

        # delete temporary csv file
        os.remove(csv_file)

        return response

    def __write_to_csv(self, csv_file, data):
        headers = self.__get_headers()

        with open(csv_file, 'w') as csvf:
            csv.writer(csvf).writerow(
                [s for s in headers.keys()])
            for d in data:
                username = d.get('username')
                amount = d.get('amount')
                promotion_bet_level = d.get('promotion_bet_level') or '-'
                created_at = d.get('created_at')
                memo = d.get('memo', '')

                rows = [
                    username,
                    f'{amount:,.2f}',
                    promotion_bet_level,
                    f'{created_at:%Y-%m-%d}',
                    memo
                ]

                csv.writer(csvf).writerow(rows)

    def __get_headers(self):
        csv_headers = {
            '会员账号': 'username',
            '总金额': 'amount',
            '晋级等级': 'promotion_bet_level',
            '创建时间': 'created_at',
            '备注': 'memo'
        }

        return csv_headers


class PromotionMemberReportWriter(object):

    def __init__(self, request):
        self.request = request
        self.params = self.request.GET.copy()
        self.game_type = int(self.params.get('game_type', '0'))

        if self.game_type == GAME_TYPE_ELECTRONICS:
            request_type = EGAME_SUMMARY_EXPORT
        elif self.game_type == GAME_TYPE_LIVE:
            request_type = LIVE_SUMMARY_EXPORT

        self.request_log = ImportExportLog.objects.create(
            game_type=self.game_type,
            request_type=request_type,
        )

    def get_summary_data(self, params):
        filters = {}
        user, user_type = parse_token_param(self.request)
        self.request_log.created_by = user
        if user_type not in {'staff', 'admin'}:
            return Summary.objects.none()

        if params.get('status'):
            filters.update(member__status=params.get('status'))

        start_date = params.get('created_at_after')
        end_date = params.get('created_at_before')
        if start_date and end_date:
            start_date = datetime.strptime(
                f'{start_date} 00:00:00', '%Y-%m-%d %H:%M:%S')

            end_date = datetime.strptime(
                f'{end_date} 23:59:59', '%Y-%m-%d %H:%M:%S')

            filters.update(member__created_at__range=(start_date, end_date))

        if params.get('username'):
            filters.update(member__username=params.get('username'))

        if params.get('username_q'):
            filters.update(member__username__contains=params.get('username_q'))

        if params.get('game_type'):
            filters.update(game_type=params.get('game_type'))

        return list(Summary.objects.filter(**filters).
                    order_by('member__username').
                    values('member__username',
                           'promotion_bet_level__name',
                           'promotion_bet_level__weekly_bonus',
                           'promotion_bet_level__monthly_bonus',
                           'total_promotion_bet',
                           'current_week_bonus',
                           'previous_week_bet_level__name',
                           'previous_month_bet_level__name',
                           'total_bonus',))

    def write_report(self):
        summary_data = self.get_summary_data(self.params)
        return self.__write_report_file(summary_data)

    def __write_report_file(self, data):
        filename = timezone.now().strftime('%Y%m%d')
        if not os.path.exists('temp_files'):  # create temp folder
            os.mkdir('temp_files')

        csv_file = f'temp_files/{filename}-推广会员报告.csv'

        # write to temporary csv file
        self.__write_to_csv(csv_file, data)

        # create zip file for the csv
        zipfile_temp = BytesIO()
        with zipfile.ZipFile(zipfile_temp, 'w') as zf:
            base_file = csv_file.split('/')[1]
            zf.write(csv_file, arcname=base_file)
        response = HttpResponse(content_type='application/zip')
        fname = f'{filename}-推广会员报告.zip'
        content_disposition = f'attachment; filename="{urlquote(fname)}"'
        response['Content-Disposition'] = content_disposition
        zipfile_temp.seek(0)
        response.write(zipfile_temp.read())

        # delete temporary csv file
        os.remove(csv_file)

        self.request_log.status = REQUEST_LOG_COMPLETED
        self.request_log.filename = f'{fname}'
        self.request_log.save()

        return response

    def __write_to_csv(self, csv_file, data):
        headers = self.__get_headers()

        with open(csv_file, 'w') as csvf:
            try:
                csv.writer(csvf).writerow(
                    [s for s in headers.keys()])
                for d in data:
                    username = d.get('username') or d.get('member__username')
                    promotion_bet_level = d.get('promotion_bet_level__name') or '-'
                    weekly_bonus = d.get('promotion_bet_level__weekly_bonus') or 0
                    monthly_bonus = d.get('promotion_bet_level__monthly_bonus') or 0
                    previous_week_bet_level = d.get(
                        'previous_week_bet_level__name') or '-'
                    previous_month_bet_level = d.get(
                        'previous_month_bet_level__name') or '-'
                    total_promotion_bet = d.get('total_promotion_bet')
                    current_week_bonus = d.get('current_week_bonus')
                    total_bonus = d.get('total_bonus')

                    csv.writer(csvf).writerow([
                        username,
                        promotion_bet_level,
                        previous_week_bet_level,
                        previous_month_bet_level,
                        f'{total_promotion_bet:,.2f}',
                        f'{current_week_bonus:,.2f}',
                        f'{weekly_bonus:,.2f}',
                        f'{current_week_bonus + weekly_bonus:,.2f}',
                        f'{monthly_bonus:,.2f}',
                        f'{total_bonus:,.2f}',
                    ])
            except Exception as exc:
                self.request_log.memo = f'{exc}'
                self.request_log.status = REQUEST_LOG_CANCELED
                self.request_log.save()

    def __get_headers(self):
        csv_headers = {
            '会员账号': 'username',
            '本周促销投注等级': 'promotion_bet_level',
            '上周促销投注等级': 'previous_week_bet_level',
            '上月促销投注等级': 'previous_month_bet_level',
            '累计有效投注': 'total_promotion_bet',
            '等级增加奖金': 'current_week_bonus',
            '周奖金': 'promotion_bet_level.weekly_bonus',
            '本周可获奖金(等级增加奖金 + 周奖金)': 'total_week_bonus',
            '月俸禄': 'promotion_bet_level.monthly_bonus',
            '总奖金': 'total_bonus'
        }

        return csv_headers


class EnvelopeClaimReportWriter(object):

    def __init__(self, request):
        self.request = request
        self.status_options = dict(STATUS_OPTIONS)
        self.event_type = None

    def get_queryset(self, data):
        filters = {}
        user, user_type = parse_token_param(self.request)
        if user_type not in {'staff', 'admin'}:
            return EnvelopeClaim.objects.none()

        try:
            self.event_type = EventType.objects.get(
                code=data.get('event_type', ''))
        except EventType.DoesNotExist:
            return EnvelopeClaim.objects.none()

        username = data.get('username_q')
        start_date = data.get('created_at_after')
        end_date = data.get('created_at_before')

        status = data.get('status')
        if status:
            filters.update(status=status)

        if start_date and end_date:
            start_date = datetime.strptime(f'{start_date}', '%Y-%m-%d')

            end_date = datetime.strptime(
                f'{end_date}', '%Y-%m-%d') + timedelta(1)

            filters.update(created_at__range=(start_date, end_date))

        if username:
            filters.update(username__contains=username)

        filters.update(event_type=self.event_type)

        if self.event_type.is_reward:
            envelope_claims = EnvelopeClaim.objects.filter(**filters).\
                values('username', 'reward__name', 'created_at__date',
                       'updated_at__date', 'status')
        else:
            envelope_claims = EnvelopeClaim.objects.filter(**filters).\
                values('username', 'created_at__date', 'updated_at__date',
                       'status').annotate(total=Sum('amount'))

        return envelope_claims

    def write_report(self):
        data = self.request.GET.copy()

        queryset = self.get_queryset(data)

        return self.__write_report_file(list(queryset))

    def __write_report_file(self, data):
        filename = timezone.now().strftime('%Y%m%d')
        if not os.path.exists('temp_files'):  # create temp folder
            os.mkdir('temp_files')

        csv_file = f'temp_files/{filename}-统计报表.csv'

        # write to temporary csv file
        self.__write_to_csv(csv_file, data)

        # create zip file for the csv
        zipfile_temp = BytesIO()
        with zipfile.ZipFile(zipfile_temp, 'w') as zf:
            base_file = csv_file.split('/')[1]
            zf.write(csv_file, arcname=base_file)
        response = HttpResponse(content_type='application/zip')
        fname = f'{filename}-统计报表.zip'
        content_disposition = f'attachment; filename="{urlquote(fname)}"'
        response['Content-Disposition'] = content_disposition
        zipfile_temp.seek(0)
        response.write(zipfile_temp.read())

        # delete temporary csv file
        os.remove(csv_file)

        return response

    def __write_to_csv(self, csv_file, data):
        headers = self.__get_headers()

        with open(csv_file, 'w') as csvf:
            csv.writer(csvf).writerow(
                [s for s in headers.keys()])
            for d in data:
                rows = []
                for value in headers.values():
                    col = d.get(value)
                    if col is None:
                        col = ''
                    elif value == 'status':
                        col = self.status_options.get(col)
                    elif value in {'created_at__date', 'updated_at__date'}:
                        col = col.strftime("%Y-%m-%d")
                    rows.append(col)
                csv.writer(csvf).writerow(rows)

    def __get_headers(self):
        csv_headers = OrderedDict()

        csv_headers.update([(u'会员账号', 'username')])
        if self.event_type.is_reward:
            csv_headers.update([(u'奖励', 'reward__name')])
        else:
            csv_headers.update([(u'红包金额', 'total')])
        csv_headers.update([
            (u'创建时间', 'created_at__date'),
            (u'更新时间', 'updated_at__date'),
            (u'状态', 'status')
        ])

        return csv_headers
