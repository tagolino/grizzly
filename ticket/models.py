from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.validators import RegexValidator
from django.db import models


class Ticket(models.Model):
    ACTIVITY_CHOICES = (
        (0, '忘记登录密码'),  # Forgot Password
        (1, '忘记取款密码'),  # Forgot Withdraw Password
        (2, '会员账号解冻'),  # Reactivate Member
        (3, '忘记会员账号'),  # Forgot Member Account
        (4, '修改银行卡'),  # Modify Bank Card
        (5, '优惠活动问题'),  # Promotion Issues
        (6, '投诉建议留言'),  # Suggestions
    )

    STATUS_PENDING = 0
    STATUS_APPROVED = 1
    STATUS_DECLINED = 2
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_DECLINED, 'Declined')
    )

    username = models.CharField(max_length=255)
    member = models.ForeignKey('account.Member', null=True,
                               blank=True, on_delete=models.SET_NULL,
                               related_name='ticket_member')
    activity = models.IntegerField(choices=ACTIVITY_CHOICES)
    activity_details = JSONField(null=True, blank=True)
    status = models.IntegerField(default=0, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User,
                                   null=True, blank=True,
                                   related_name='ticket_updated_by',
                                   on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True,
                                      null=True, blank=True)
    memo = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'ticket'
        permissions = (('list_ticket', 'Can list ticket'),)
