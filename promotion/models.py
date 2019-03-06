from __future__ import unicode_literals

import os

from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Max
from django.db.models.functions import Coalesce

from grizzly.utils import PathAndRename


STATUS_OPTION = (
    (0, 'Inactive'),
    (1, 'Active'),
)

PLATFORM_OPTIONS = (
    (0, 'MOBILE'),
    (1, 'DESKTOP'),
    (2, 'ALL'),
)

CLAIM_STATUS_OPTION = (
    (0, 'Pending'),
    (1, 'Accept'),
    (2, 'Reject'),
)

GAME_TYPE_ELECTRONICS = 0
GAME_TYPE_LIVE = 1
GAME_TYPE_OPTIONS = (
    (GAME_TYPE_ELECTRONICS, 'Electronics'),
    (GAME_TYPE_LIVE, 'Live'),
)


def image_directory(filename):
    """
    :return: cms/example.com/home-page/content.jpg
    """
    upload_dir = os.path.join('promotion', 'image')
    return os.path.join(upload_dir, filename)


class Announcement(models.Model):
    '''
    '''

    name = models.CharField(max_length=255, null=True, blank=True)
    announcement = models.TextField(blank=True)
    status = models.IntegerField(default=1, null=True,
                                 blank=True, choices=STATUS_OPTION)
    rank = models.IntegerField(default=1, null=True, blank=True)
    platform = models.IntegerField(default=1, null=True,
                                   blank=True, choices=PLATFORM_OPTIONS)
    created_by = models.ForeignKey(User, null=True, blank=True,
                                   related_name='promotion_created_by',
                                   on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User,
                                   null=True, blank=True,
                                   related_name='promotion_updated_by',
                                   on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True,
                                      null=True, blank=True)

    class Meta:
        db_table = 'promote_announcement'
        permissions = (('list_announcement', 'Can list announcement'),)


class PromotionClaim(models.Model):
    username = models.CharField(max_length=255,
                                null=True,
                                blank=True,
                                validators=[RegexValidator(
                                    regex='^[a-zA-Z0-9][a-zA-Z0-9_\-]+$',
                                    message='Username should contain '
                                            'Alphanumeric, _ or - and '
                                            'should start with '
                                            'letter or digit')])
    promotion_id = models.CharField(max_length=255, null=True, blank=True)
    game_name = models.CharField(max_length=255, null=True, blank=True)
    claim_forms = JSONField(null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True,
                                   related_name='claim_created_by',
                                   on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User,
                                   null=True, blank=True,
                                   related_name='claim_updated_by',
                                   on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True,
                                      null=True, blank=True)
    status = models.IntegerField(default=0, null=True,
                                 blank=True, choices=CLAIM_STATUS_OPTION)
    memo = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'promote_promotionclaim'
        permissions = (('list_promotionclaim', 'Can list promotionclaim'),)


class Promotion(models.Model):
    promotion_name = models.CharField(max_length=255,
                                      null=True,
                                      blank=True)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    status = models.IntegerField(default=1, choices=STATUS_OPTION)
    desktop_icon = models.ImageField(null=True,
                                     blank=True,
                                     upload_to=PathAndRename(
                                         'promotion_desktop_icons'))
    mobile_icon = models.ImageField(null=True,
                                    blank=True,
                                    upload_to=PathAndRename(
                                        'promotion_mobile_icons'))
    rules = models.TextField(null=True, blank=True)
    rank = models.IntegerField(default=1, null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True,
                                   related_name='promotions_created_by',
                                   on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, null=True, blank=True,
                                   related_name='promotions_updated_by',
                                   on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True,
                                      null=True, blank=True)

    class Meta:
        db_table = 'promote_promotion'
        permissions = (('list_promotion', 'Can list promotion'),)

    def __str__(self):
        return self.promotion_name

    def save(self, *args, **kwargs):
        if self.pk is None:
            promotions = Promotion.objects.all().order_by('-rank')
            if promotions.exists():
                self.rank = promotions.first().rank + 1
        super().save(*args, **kwargs)


class PromotionElement(models.Model):
    TYPE_STR = 0
    TYPE_CHECKBOX = 1
    TYPE_RADIO = 2
    TYPE_SELECT = 3
    TYPE_DATE = 4
    TYPE_DATE_RANGE = 5
    TYPE_NUMBER = 6

    TYPE_CHOICES = (
        (TYPE_STR, 'String'),
        (TYPE_CHECKBOX, 'Checkbox'),
        (TYPE_RADIO, 'Radio'),
        (TYPE_SELECT, 'Select'),
        (TYPE_DATE, 'Date'),
        (TYPE_DATE_RANGE, 'DateRange'),
        (TYPE_NUMBER, 'Number')
    )

    name = models.CharField(max_length=255, null=True, blank=True)
    is_required = models.BooleanField(default=False)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    type = models.IntegerField(default=TYPE_STR, choices=TYPE_CHOICES)
    value = models.CharField(max_length=255, null=True, blank=True)
    placeholder = models.CharField(max_length=255, null=True, blank=True)
    memo = models.TextField(null=True, blank=True)
    rank = models.IntegerField(default=1, null=True, blank=True)
    promotion = models.ForeignKey('Promotion',
                                  related_name='promo_items',
                                  on_delete=models.CASCADE)

    class Meta:
        db_table = 'promote_promotion_element'
        permissions = (
            ('list_promotionelement', 'Can list promotion element'),)
        ordering = ('rank',)

    def save(self, *args, **kwargs):
        if self.pk is None:
            promotion_items = PromotionElement.objects.filter(
                promotion=self.promotion).order_by('-rank')
            if promotion_items.exists():
                self.rank = promotion_items.first().rank + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class PromotionBetLevel(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    total_bet = models.FloatField(default=0.0)
    bonus = models.FloatField(default=0.0)
    weekly_bonus = models.FloatField(default=0.0)
    monthly_bonus = models.FloatField(default=0.0)
    game_type = models.IntegerField(default=0,
                                    null=True, blank=True,
                                    choices=GAME_TYPE_OPTIONS)

    class Meta:
        db_table = 'promote_promotionbetlevel'
        permissions = (
            ('list_promotionbetlevel', 'Can list promotionbetlevel'),)

    def __str__(self):
        return self.name


class PromotionBet(models.Model):
    member = models.ForeignKey('account.Member', null=True, blank=True,
                               related_name='bet_member',
                               on_delete=models.SET_NULL)
    username = models.CharField(max_length=100, null=True, blank=True)
    game_type = models.IntegerField(default=0,
                                    null=True, blank=True,
                                    choices=GAME_TYPE_OPTIONS)
    amount = models.FloatField(default=0.0)
    created_by = models.ForeignKey(User, null=True, blank=True,
                                   related_name='bet_created_by',
                                   on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User,
                                   null=True, blank=True,
                                   related_name='bet_updated_by',
                                   on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True,
                                      null=True, blank=True)
    promotion_bet_level = models.ForeignKey(PromotionBetLevel,
                                            null=True, blank=True,
                                            related_name='promotion_betlevel',
                                            on_delete=models.SET_NULL)
    cycle_begin = models.DateTimeField(blank=True, null=True)
    cycle_end = models.DateTimeField(blank=True, null=True)
    memo = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'promote_promotionbet'
        permissions = (('list_promotionbet', 'Can list promotionbet'),)

    def __str__(self):
        created_data = f'{self.created_at:%Y-%m-%d}'
        return f'{self.username} - {self.amount:.2f} ({created_data})'


class PromotionBetMonthly(models.Model):
    member = models.ForeignKey('account.Member', null=True, blank=True,
                               related_name='monthly_bet_member',
                               on_delete=models.SET_NULL)
    total_bet = models.FloatField(default=0.0)
    promotion_bet_level = models.ForeignKey(PromotionBetLevel,
                                            null=True, blank=True,
                                            related_name='monthly_bet_level',
                                            on_delete=models.SET_NULL)
    cycle_year = models.IntegerField(blank=True, null=True)
    cycle_month = models.IntegerField(blank=True, null=True)
    cycle_begin = models.DateTimeField(blank=True, null=True)
    cycle_end = models.DateTimeField(blank=True, null=True)
    game_type = models.IntegerField(default=0,
                                    null=True, blank=True,
                                    choices=GAME_TYPE_OPTIONS)

    class Meta:
        db_table = 'promote_promotionbetmonthly'
        permissions = (
            ('list_promotionbet_monthly', 'Can list promotionbet_monthly'),)

    def __str__(self):
        return f'{self.member} - ({self.cycle_month} {self.cycle_year})'


class Summary(models.Model):
    member = models.ForeignKey('account.Member', null=True, blank=True,
                               related_name='member_bet_summary',
                               on_delete=models.SET_NULL)
    game_type = models.IntegerField(default=0,
                                    null=True, blank=True,
                                    choices=GAME_TYPE_OPTIONS)
    promotion_bet_level = models.ForeignKey(PromotionBetLevel,
                                            null=True, blank=True,
                                            related_name='summary_betlevel',
                                            on_delete=models.SET_NULL)
    previous_week_bet_level = models.ForeignKey(PromotionBetLevel,
                                                null=True, blank=True,
                                                related_name='summary_prev_week_level',
                                                on_delete=models.SET_NULL)
    previous_month_bet_level = models.ForeignKey(PromotionBetLevel,
                                                 null=True, blank=True,
                                                 related_name='summary_prev_month_level',
                                                 on_delete=models.SET_NULL)
    total_promotion_bet = models.FloatField(default=0.0)
    total_promotion_bonus = models.FloatField(default=0.0)
    current_week_bonus = models.FloatField(default=0.0)

    class Meta:
        db_table = 'promote_summary'
        permissions = (
            ('list_summary', 'Can list summary'),)

    def __str__(self):
        game_type = dict(GAME_TYPE_OPTIONS).get(self.game_type)
        return f'{self.member.username} - {game_type}'
