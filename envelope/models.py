from __future__ import unicode_literals

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

ENVELOPE_TYPE_OPTIONS = (
    (TYPE_ENVELOPE, 'Envelope'),
    (TYPE_EGG, 'Egg'),
    (TYPE_PIGGYBANK, 'Piggy Bank'),
)


class EnvelopeClaimManager(models.Manager):
    # Don't know if this is the right way on using manager

    def claims_today(self):
        today = timezone.now().date()
        amount = self.filter(created_at__date=today)

        if not amount.exists():
            return 0

        return amount.aggregate(Sum('amount')).get('amount__sum', 0)

    def remaining_pool_amount(self, envelope_type):
        envelope_type_desc = dict(
            ENVELOPE_TYPE_OPTIONS).get(envelope_type, 'envelope').lower()
        pool_amount = GlobalPreference.objects.\
            get_value(f'{envelope_type_desc}_pool_amount')

        if pool_amount is None:
            pool_amount = 0

        return float(pool_amount) - self.claims_today()

    def get_threshold_range(self, username, envelope_type):
        today = timezone.now().date()

        deposit = EnvelopeDeposit.objects.filter(
            username=username,
            created_at__date=today,
            envelope_type=envelope_type
            ).aggregate(Sum('amount')).get('amount__sum', 0)

        return EnvelopeAmountSetting.objects.filter(
            threshold_amount__lte=deposit,
            envelope_type=envelope_type).values(
                'threshold_amount',
                'min_amount',
                'max_amount'
            ).order_by('-threshold_amount').first()

    def get_quantity_left(self, username, envelope_type):
        quantity = 0
        today = timezone.now().date()
        claim = self.filter(created_at__date=today,
                            username=username,
                            envelope_type=envelope_type)

        # Get user's today deposit(s)
        user_deposit = EnvelopeDeposit.objects.\
            filter(username=username,
                   envelope_type=envelope_type,
                   created_at__date=today)

        if not user_deposit.exists():
            return 0

        # Get total
        deposit = user_deposit.aggregate(Sum('amount')).get('amount__sum', 0)

        if deposit == 0:
            return 0

        # Get levels
        levels = EnvelopeLevel.objects.filter(envelope_type=envelope_type).\
            values('amount', 'quantity').order_by('-amount')

        # Get X time to claim amount
        for level in levels:
            if deposit < level['amount']:
                continue
            else:
                quantity = level['quantity']
                break

        if claim.exists():
            claim = claim.count()
        else:
            claim = 0

        if claim < quantity:
            # return claim left
            return quantity - claim
        else:
            return 0


class EnvelopeClaim(models.Model):
    username = models.CharField(max_length=255, null=True, blank=True)
    amount = models.FloatField(default=0.0)
    envelope_type = models.IntegerField(default=0,
                                        null=True, blank=True,
                                        choices=ENVELOPE_TYPE_OPTIONS)
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

    def __str__(self):
        return self.name


class EnvelopeDeposit(models.Model):
    username = models.CharField(max_length=100, null=True, blank=True)
    amount = models.FloatField(default=0.0)
    envelope_type = models.IntegerField(default=0,
                                        null=True, blank=True,
                                        choices=ENVELOPE_TYPE_OPTIONS)
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
