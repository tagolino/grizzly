from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.db import models


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
    username = models.CharField(max_length=255, null=True, blank=True)
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
