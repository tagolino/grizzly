import logging

from calendar import monthrange
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.utils import timezone

from grizzly.celery import app
from envelope.models import (EnvelopeDeposit)


logger = logging.getLogger(__name__)


@app.task(name='envelope_deposit_import')
def envelope_deposit_import(import_data, user_id, envelope_type):
    user = User.objects.get(id=user_id)
    logger.info(user)

    for data in import_data:
        logger.info(data)

        envelope_data = {
            'username': data['username'],
            'amount': data['amount'],
            'envelope_type': envelope_type,
            'created_by': user,
        }

        EnvelopeDeposit.objects.create(**envelope_data)

        logger.info(envelope_data)
