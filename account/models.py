from django.contrib.auth.models import User, Group
from django.db import models
from django.utils import timezone

from promotion.models import PromotionBetLevel


STAFF_STATUS_OPTIONS = (
    (0, 'Inactive'),
    (1, 'Active'),
)


class Staff(models.Model):
    '''
    @class Staff
    @brief
        Staff model class
    '''
    user = models.OneToOneField(User, null=True, blank=True,
                                related_name='staff_user',
                                on_delete=models.SET_NULL)
    username = models.CharField(unique=True, max_length=100,
                                null=True, blank=True)
    email = models.EmailField(max_length=70,
                              blank=True, null=True,
                              default=None)
    memo = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now=False, auto_now_add=True)
    created_by = models.ForeignKey(User, null=True, blank=True,
                                   related_name='staff_created_by',
                                   on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True, auto_now_add=False,
                                      null=True, blank=True)
    updated_by = models.ForeignKey(User,
                                   null=True, blank=True,
                                   related_name='staff_updated_by',
                                   on_delete=models.SET_NULL)
    is_logged_in = models.NullBooleanField(default=False,
                                           null=True, blank=True)
    status = models.IntegerField(default=1,
                                 null=True, blank=True,
                                 choices=STAFF_STATUS_OPTIONS)
    group = models.ForeignKey(Group, related_name="staff_group",
                              on_delete=models.SET_NULL, null=True,
                              blank=True)

    class Meta:
        db_table = 'account_staff'
        permissions = (('list_staff', 'Can list staff'),)

    def __str__(self):
        return self.username


class Member(models.Model):
    '''
    @class Member
    @brief
        Member model class
    '''
    username = models.CharField(unique=True, max_length=100,
                                null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, null=True, blank=True,
                                   related_name='member_created_by',
                                   on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True,
                                      null=True, blank=True)
    updated_by = models.ForeignKey(User,
                                   null=True, blank=True,
                                   related_name='member_updated_by',
                                   on_delete=models.SET_NULL)
    promotion_bet_level = models.ForeignKey(PromotionBetLevel,
                                            null=True, blank=True,
                                            related_name='member_betlevel',
                                            on_delete=models.SET_NULL)
    previous_week_bet_level = models.ForeignKey(PromotionBetLevel,
                                                null=True, blank=True,
                                                related_name='member_prev_week_level',
                                                on_delete=models.SET_NULL)
    previous_month_bet_level = models.ForeignKey(PromotionBetLevel,
                                                 null=True, blank=True,
                                                 related_name='member_prev_month_level',
                                                 on_delete=models.SET_NULL)
    total_promotion_bet = models.FloatField(default=0.0)
    total_promotion_bonus = models.FloatField(default=0.0)
    current_week_bonus = models.FloatField(default=0.0)
    total_bonus = models.FloatField(default=0.0)
    memo = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'account_member'
        permissions = (('list_member', 'Can list member'),)

    def __str__(self):
        return self.username
