import csv
import logging
import os
import zipfile

from datetime import datetime
from django.http import HttpResponse
from django.utils import timezone
from django.utils.http import urlquote
from django.utils.translation import ugettext as _
from io import BytesIO

from grizzly.lib import constants
from grizzly.utils import get_user_type
from loginsvc.views import generate_response
from oauth2_provider.models import AccessToken
from promotion.models import PromotionClaim
from promotion.serializers import PromotionClaimAdminSerializer


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

        username = data.get('username_q')
        game_name = data.get('game_name')
        start_date = data.get('created_at_after')
        end_date = data.get('created_at_before')

        status = data.get('status')
        if status:
            filters.update(status=status)

        claims = PromotionClaim.objects.filter(**filters)

        if start_date and end_date:
            start_date = datetime.strptime(
                f'{start_date} 00:00:00', '%Y-%m-%d %H:%M:%S')

            end_date = datetime.strptime(
                f'{end_date} 23:59:59', '%Y-%m-%d %H:%M:%S')

            claims = claims.filter(created_at__range=(start_date, end_date))

        if username:
            claims = claims.filter(username__contains=username)

        if game_name:
            claims = claims.filter(game_name__contains=game_name)

        return claims

    def write_report(self):
        data = self.request.GET.copy()

        queryset = self.get_queryset(data)
        context = {'request': self.request}
        serializer = PromotionClaimAdminSerializer(queryset,
                                                   context=context,
                                                   many=True)

        return self.__write_report_file(list(serializer.data))

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
                    elif value in {'created_at', 'updated_at'}:
                        col = col[:19].replace('T', ' ')
                    elif isinstance(col, dict):
                        col_values = []
                        for form_key, form_value in col.items():
                            try:
                                if isinstance(form_value, list):
                                    form_value = ', '.join(form_value)
                            except Exception as exc:
                                logger.error(exc)
                            col_values.append(f'{form_key}: {form_value}')
                        col = '; '.join(col_values)

                    rows.append(col)
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
