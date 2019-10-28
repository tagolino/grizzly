from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt

from grizzly.lib import constants
from loginsvc.views import generate_response
from report.utils.writer import (PromotionBetReportWriter,
                                 PromotionClaimReportWriter,
                                 PromotionMemberReportWriter,
                                 EnvelopeClaimReportWriter,)


@csrf_exempt
def export_report(request):
    report_type = request.GET.get('report')

    reports = {
        'promotion_claims': PromotionClaimReportWriter(request),
        'promotion_bets': PromotionBetReportWriter(request),
        'promotion_member': PromotionMemberReportWriter(request),
        'envelope_claims': EnvelopeClaimReportWriter(request),
    }

    report_writer = reports.get(report_type, None)

    if not report_writer:
        return generate_response(constants.NOT_ALLOWED,
                                 _('Request not allowed'))

    return report_writer.write_report()
