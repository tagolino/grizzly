from __future__ import unicode_literals

import logging
import random

from datetime import datetime
from django.utils import timezone
from django.db.models import Sum
from django.contrib.auth.models import User
from django.db import models

from configsetting.models import GlobalPreference

CLAIM_STATUS_OPTION = (
    (0, 'Pending'),
    (1, 'Accept'),
    (2, 'Reject'),
)

TYPE_ENVELOPE = 0
TYPE_EGG = 1
TYPE_PIGGYBANK = 2
TYPE_WHEEL = 3

ENVELOPE_TYPE_OPTIONS = (
    (TYPE_ENVELOPE, 'Envelope'),
    (TYPE_EGG, 'Egg'),
    (TYPE_PIGGYBANK, 'Piggy Bank'),
    (TYPE_WHEEL, 'Spin The Wheel'),
)


TYPE_ENVELOPE_DEPOSIT_IMPORT = 0
TYPE_ENVELOPE_CLAIM_EXPORT = 1

REQUEST_TYPE_OPTIONS = (
    (TYPE_ENVELOPE_DEPOSIT_IMPORT, 'Import Member Deposits'),
    (TYPE_ENVELOPE_CLAIM_EXPORT, 'Export Member Claims'),
)

REQUEST_LOG_STATUS_OPTIONS = (
    (0, 'On-going'),
    (1, 'Completed'),
    (2, 'Canceled'),
)


logger = logging.getLogger(__name__)


class EventType(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    code = models.CharField(max_length=255)
    is_active = models.BooleanField(default=1)
    date_from = models.DateField(null=True, blank=True)
    time_from = models.TimeField(default='00:00:00')
    date_to = models.DateField(null=True, blank=True)
    time_to = models.TimeField(default='23:59:59')
    is_daily = models.BooleanField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, null=True, blank=True,
                                   related_name='event_type_created_by',
                                   on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True,
                                      null=True, blank=True)
    updated_by = models.ForeignKey(User, null=True, blank=True,
                                   related_name='event_type_updated_by',
                                   on_delete=models.SET_NULL)
    memo = models.TextField(null=True, blank=True)
    is_reward = models.BooleanField(default=0)

    def __str__(self):
        return self.name


class Reward(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    amount = models.FloatField(default=0.0)
    envelope_type = models.IntegerField(default=0,
                                        null=True, blank=True,
                                        choices=ENVELOPE_TYPE_OPTIONS)
    event_type = models.ForeignKey(EventType,
                                   null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name='reward_event_type')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True,
                                      null=True, blank=True)
    chance = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class EnvelopeClaimManager(models.Manager):
    SMALL_AMOUNTS = 0
    MEDIUM_AMOUNTS = 1
    LARGE_AMOUNTS = 2
    SMALL_CHANCE = 0.9
    MEDIUM_CHANCE = 0.08
    LARGE_CHANCE = 0.02

    def get_claims_total_amount_today(self, event_type):
        today = timezone.localtime(timezone.now()).date()
        amount = self.filter(created_at__date=today, event_type=event_type)

        if not amount.exists():
            return 0

        return amount.aggregate(Sum('amount')).get('amount__sum', 0)

    def remaining_pool_amount(self, event_type):
        pool_amount = GlobalPreference.objects.\
            get_value(f'{event_type.code}_pool_amount')

        if pool_amount is None:
            pool_amount = 0

        claims_total_amount_today = self.get_claims_total_amount_today(
            event_type)

        return float(pool_amount) - claims_total_amount_today

    @staticmethod
    def get_deposit(username, event_type):
        today = timezone.localtime(timezone.now()).date()

        deposit = EnvelopeDeposit.objects.filter(
            username=username,
            created_at__date=today,
            event_type=event_type
        ).aggregate(Sum('amount')).get('amount__sum', 0)

        return deposit or 0

    def get_threshold_range(self, username, event_type):
        deposit = self.get_deposit(username, event_type)

        claim_amount_from = GlobalPreference.objects.\
            get_value(f'{event_type.code}_claim_amount_from')
        claim_amount_to = GlobalPreference.objects.\
            get_value(f'{event_type.code}_claim_amount_to')

        envelope_amount_setting = EnvelopeAmountSetting.objects.filter(
            threshold_amount__lte=deposit,
            event_type=event_type).values(
                'threshold_amount',
                'min_amount',
                'max_amount'
            ).order_by('-threshold_amount')

        if envelope_amount_setting.exists():
            amount_treshold = envelope_amount_setting.first()
            return (float(amount_treshold.get('min_amount', 0)),
                    float(amount_treshold.get('max_amount', 0)))

        return (float(claim_amount_from), float(claim_amount_to))

    def get_quantity_left(self, username, event_type):
        quantity = 0
        today = timezone.localtime(timezone.now())
        start_date = event_type.date_from or today.date()
        end_date = event_type.date_to or today.date()
        start_time = event_type.time_from
        end_time = event_type.time_to

        if not event_type.is_active:
            return None
        elif event_type.is_daily:
            date_check = start_date <= today.date() <= end_date
            time_check = start_time <= today.time() <= end_time

            if not (date_check and time_check):
                return None
        else:
            event_from = datetime.strptime(
                f'{start_date:%Y-%m-%d} {start_time:%H:%M:%S}',
                '%Y-%m-%d %H:%M:%S')

            event_to = datetime.strptime(
                f'{end_date:%Y-%m-%d} {end_time:%H:%M:%S}',
                '%Y-%m-%d %H:%M:%S')

            if not event_from <= today.replace(tzinfo=None) <= event_to:
                return None

        filters = {
            'created_at__date': today.date(),
            'username': username,
            'event_type': event_type,
        }

        # Get user's today deposit(s)
        user_deposit = self.get_deposit(username, event_type)

        if user_deposit == 0:
            return 0

        # Get levels
        levels = EnvelopeLevel.objects.filter(event_type=event_type).\
            values('amount', 'quantity').order_by('-amount')

        # Get X time to claim amount
        quantity = 0
        for level in levels:
            if user_deposit < level['amount']:
                continue
            else:
                quantity = level['quantity']
                break

        claim_frequency = GlobalPreference.objects.list(
            f'{event_type.code}_claim_frequency')
        if claim_frequency and quantity:
            claim_frequency = claim_frequency[0].split('/')
            claim_count_allow = int(claim_frequency[0])
            claim_rate = claim_frequency[1].split('.')

            _value = getattr(today, claim_rate[1])
            filters.update({f'created_at__{claim_rate[1]}': _value})

            claim = self.filter(**filters).count()
            if claim_count_allow <= claim:
                return 0
            return claim_count_allow - claim

        claim = self.filter(**filters)

        if claim.exists():
            claim = claim.count()
        else:
            claim = 0

        if claim < quantity:
            # return claim left
            return quantity - claim
        else:
            return 0

    def get_claim_amount(self, event_type, amount_threshold):
        amount_sizes = [
            self.SMALL_AMOUNTS,
            self.MEDIUM_AMOUNTS,
            self.LARGE_AMOUNTS
        ]
        chances = [
            self.SMALL_CHANCE,
            self.MEDIUM_CHANCE,
            self.LARGE_CHANCE
        ]
        amount_size_choice = random.choices(amount_sizes, weights=chances)[0]

        min_claim, max_claim = amount_threshold
        amounts = [n for n in range(int(min_claim), int(max_claim) + 1)]

        amount_count = len(amounts)
        chunks = int(amount_count / len(amount_sizes))

        chunk_amounts = [
            amounts[x:x + chunks] for x in range(0, amount_count, chunks)]
        claim_amounts = chunk_amounts[amount_size_choice]

        return round(random.uniform(
                claim_amounts[0], claim_amounts[-1]), 2)

    def get_reward(self, event_type):
        rewards = Reward.objects.filter(event_type=event_type)
        chances = [reward.chance for reward in rewards]

        return random.choices(rewards, weights=chances)[0]

    def get_event_type(self, event_type):
        try:
            return EventType.objects.get(code=event_type)
        except EventType.DoesNotExist:
            return None


class EnvelopeClaim(models.Model):
    username = models.CharField(max_length=255, null=True, blank=True)
    amount = models.FloatField(default=0.0)
    reward = models.ForeignKey(Reward, null=True, blank=True,
                               related_name='envelope_reward',
                               on_delete=models.SET_NULL)
    envelope_type = models.IntegerField(default=0,
                                        null=True, blank=True,
                                        choices=ENVELOPE_TYPE_OPTIONS)
    event_type = models.ForeignKey(EventType,
                                   null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name='claim_event_type')
    created_by = models.ForeignKey(User, null=True, blank=True,
                                   related_name='envelope_claim_created_by',
                                   on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User,
                                   null=True, blank=True,
                                   related_name='envelope_claim_updated_by',
                                   on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True,
                                      null=True, blank=True)
    status = models.IntegerField(default=0, null=True,
                                 blank=True, choices=CLAIM_STATUS_OPTION)
    memo = models.TextField(null=True, blank=True)

    objects = EnvelopeClaimManager()


class EnvelopeLevel(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    amount = models.FloatField(default=0.0)
    quantity = models.IntegerField(default=0)
    envelope_type = models.IntegerField(default=0,
                                        null=True, blank=True,
                                        choices=ENVELOPE_TYPE_OPTIONS)
    event_type = models.ForeignKey(EventType,
                                   null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name='level_event_type')

    def __str__(self):
        return self.name


class EnvelopeDeposit(models.Model):
    username = models.CharField(max_length=100, null=True, blank=True)
    amount = models.FloatField(default=0.0)
    envelope_type = models.IntegerField(default=0,
                                        null=True, blank=True,
                                        choices=ENVELOPE_TYPE_OPTIONS)
    event_type = models.ForeignKey(EventType,
                                   null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name='deposit_event_type')
    created_by = models.ForeignKey(User, null=True, blank=True,
                                   related_name='envelope_deposit_created_by',
                                   on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User,
                                   null=True, blank=True,
                                   related_name='envelope_deposit_updated_by',
                                   on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True,
                                      null=True, blank=True)
    memo = models.TextField(null=True, blank=True)
    request = models.ForeignKey('RequestLog', null=True, blank=True,
                                related_name='envelope_deposit_requestlog',
                                on_delete=models.SET_NULL)

    def __str__(self):
        created_data = f'{self.created_at:%Y-%m-%d}'
        return f'{self.username} - {self.amount:.2f} ({created_data})'


class EnvelopeAmountSetting(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    threshold_amount = models.FloatField(default=0.0)
    min_amount = models.FloatField(default=0.0)
    max_amount = models.FloatField(default=0.0)
    envelope_type = models.IntegerField(default=0,
                                        null=True, blank=True,
                                        choices=ENVELOPE_TYPE_OPTIONS)
    event_type = models.ForeignKey(EventType,
                                   null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name='setting_event_type')
    created_by = models.ForeignKey(
        User, null=True, blank=True,
        related_name='envelope_amount_setting_created_by',
        on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        User, null=True, blank=True,
        related_name='envelope_amount_setting_updated_by',
        on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True,
                                      null=True, blank=True)

    def __str__(self):
        return self.name


class RequestLog(models.Model):
    event_type = models.ForeignKey('EventType', null=True, blank=True,
                                   related_name='event_type_requestlog',
                                   on_delete=models.SET_NULL)
    request_type = models.IntegerField(null=True, blank=True,
                                       choices=REQUEST_TYPE_OPTIONS)
    status = models.IntegerField(default=0,
                                 null=True, blank=True,
                                 choices=REQUEST_LOG_STATUS_OPTIONS)
    memo = models.TextField(null=True, blank=True)
    filename = models.CharField(max_length=255,
                                null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True,
                                   related_name='requestlog_createdby',
                                   on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True,
                                      null=True, blank=True)

    class Meta:
        db_table = 'envelope_requestlog'
        permissions = (('list_requestlog', 'Can list request log'),)

    def __str__(self):
        return f'{self.request_type } - {self.created_at:%Y/%m/%d %H:%M:%S}'
