from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from grizzly.lib import constants
from loginsvc.views import generate_response
from report.utils.writer import PromotionClaimReportWriter


@csrf_exempt
def export_report(request):
    report_type = request.GET.get('report')

    if report_type == 'promotion_claims':
        report_writer = PromotionClaimReportWriter(request)
    else:
        return generate_response(constants.NOT_ALLOWED,
                                 _('Request not allowed'))

    return report_writer.write_report()
