import csv
import logging
import os
import zipfile

from datetime import datetime, timedelta
from django.http import HttpResponse
from django.utils import timezone
from django.utils.http import urlquote
from django.db.models import Sum
from io import BytesIO

from account.models import Member
from grizzly.utils import get_user_type
from oauth2_provider.models import AccessToken
from promotion.models import (GAME_TYPE_ELECTRONICS,
                              PromotionBet,
                              PromotionClaim,
                              Summary)
from envelope.models import (EnvelopeClaim)


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

    def get_member_data(self, params):
        filters = {}
        user, user_type = parse_token_param(self.request)

        if user_type not in {'staff', 'admin'}:
            return Member.objects.none()

        if params.get('status'):
            filters.update(status=params.get('status'))

        start_date = params.get('created_at_after')
        end_date = params.get('created_at_before')
        if start_date and end_date:
            start_date = datetime.strptime(
                f'{start_date} 00:00:00', '%Y-%m-%d %H:%M:%S')

            end_date = datetime.strptime(
                f'{end_date} 23:59:59', '%Y-%m-%d %H:%M:%S')

            filters.update(created_at__range=(start_date, end_date))

        if params.get('username'):
            filters.update(username=params.get('username'))

        if params.get('username_q'):
            filters.update(username__contains=params.get('username_q'))

        return list(Member.objects.filter(**filters).
                    order_by('username').
                    values('username',
                           'promotion_bet_level__name',
                           'total_promotion_bet',
                           'current_week_bonus',
                           'previous_week_bet_level__name',
                           'previous_month_bet_level__name'))

    def get_summary_data(self, params):
        filters = {}
        user, user_type = parse_token_param(self.request)
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
                           'total_promotion_bet',
                           'current_week_bonus',
                           'previous_week_bet_level__name',
                           'previous_month_bet_level__name'))

    def write_report(self):
        params = self.request.GET.copy()

        if int(params.get('game_type', '0')) == GAME_TYPE_ELECTRONICS:
            return self.__write_report_file(self.get_member_data(params))
        else:
            return self.__write_report_file(self.get_summary_data(params))

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

        return response

    def __write_to_csv(self, csv_file, data):
        headers = self.__get_headers()

        with open(csv_file, 'w') as csvf:
            csv.writer(csvf).writerow(
                [s for s in headers.keys()])
            for d in data:
                username = d.get('username') or d.get('member__username')
                promotion_bet_level = d.get('promotion_bet_level__name') or '-'
                previous_week_bet_level = d.get(
                    'previous_week_bet_level__name') or '-'
                previous_month_bet_level = d.get(
                    'previous_month_bet_level__name') or '-'
                total_promotion_bet = d.get('total_promotion_bet')
                current_week_bonus = d.get('current_week_bonus')

                csv.writer(csvf).writerow([
                    username,
                    promotion_bet_level,
                    previous_week_bet_level,
                    previous_month_bet_level,
                    f'{total_promotion_bet:,.2f}',
                    f'{current_week_bonus:,.2f}',
                ])

    def __get_headers(self):
        csv_headers = {
            '会员账号': 'username',
            '本周 促销投注等级': 'promotion_bet_level',
            '上周促销投注等级': 'previous_week_bet_level',
            '上月 促销投注等级': 'previous_month_bet_level',
            '累计有效投注': 'total_promotion_bet',
            '总促销奖金': 'current_week_bonus'
        }

        return csv_headers


class EnvelopeClaimReportWriter(object):

    def __init__(self, request):
        self.request = request
        self.status_options = dict(STATUS_OPTIONS)

    def get_queryset(self, data):
        filters = {}
        user, user_type = parse_token_param(self.request)
        if user_type not in {'staff', 'admin'}:
            return EnvelopeClaim.objects.none()

        envelope_type = data.get('type', 0)
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

        filters.update(envelope_type=envelope_type)

        envelope_claims = EnvelopeClaim.objects.filter(**filters).\
            values('username', 'created_at__date', 'updated_at__date',
                   'status').\
            annotate(total=Sum('amount'))

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
        csv_headers = {
            '会员账号': 'username',
            '红包金额': 'total',
            '创建时间': 'created_at__date',
            '更新时间': 'updated_at__date',
            '状态': 'status'
        }

        return csv_headers
