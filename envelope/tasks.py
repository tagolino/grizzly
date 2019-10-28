import logging

from calendar import monthrange
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.utils import timezone

from grizzly.celery import app
from envelope.models import (EnvelopeDeposit,
                             EventType,
                             RequestLog,
                             )


logger = logging.getLogger(__name__)


@app.task(name='envelope_deposit_import')
def envelope_deposit_import(import_data, user_id, event_type, request_log_id):
    user = User.objects.get(id=user_id)
    event_type = EventType.objects.get(id=event_type)
    request_log = RequestLog.objects.get(id=request_log_id)
    deposits = []
    logger.info(user)

    for data in reversed(import_data):
        logger.info(data)
        deposits.append(
            EnvelopeDeposit(
                username=data.get('username'),
                amount=data.get('amount', 0),
                event_type=event_type,
                created_by=user,
                request=request_log,
            )
        )

    try:
        envelope_deposits = EnvelopeDeposit.objects.bulk_create(deposits)
        logger.info(f'{len(envelope_deposits)} envelope deposits created')

        request_log.status = 1
        request_log.save(update_fields=['status', 'updated_at'])
    except Exception as exc:
        logger.error(exc)
        request_log.status = 2
        request_log.memo = f'Error: {exc}'
        request_log.save(update_fields=['status', 'memo', 'updated_at'])


@app.task(name='envelope_cancel_request')
def cancel_request(request_log_id):
    STATUS_ONGOING = 0
    request_log = RequestLog.objects.get(id=request_log_id)
    if request_log.status == STATUS_ONGOING:
        request_log.status = 2
        request_log.memo = f'Request canceled'
        request_log.save(update_fields=['status', 'memo', 'updated_at'])
