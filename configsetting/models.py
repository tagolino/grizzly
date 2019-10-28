import os
from django.db import models
from django.core.validators import RegexValidator
from django.contrib.postgres.fields import JSONField
from django.utils.translation import ugettext_lazy as _


def get_pref_img_dir(instance, filename):
    upload_dir = os.path.join('preferences', 'image')
    return os.path.join(upload_dir, filename)


class GlobalPreferencesManager(models.Manager):
    def list(self, key: str, separator=','):
        """List multiple string-type sub-values"""

        try:
            value = self.get(key=key).value
        except GlobalPreference.DoesNotExist:
            # fixtures not yet loaded
            return []

        return value.split(separator) if value else []

    def get_value(self, key: str):
        try:
            inst = self.get(key=key)
            if inst.type == GlobalPreference.TYPE_IMAGE:
                value = inst.image
            else:
                value = inst.value
        except GlobalPreference.DoesNotExist:
            # fixtures not yet loaded
            return None
        return value


class GlobalPreference(models.Model):
    TYPE_STR = 1
    TYPE_IMAGE = 2
    TYPE_BOOLEAN = 3
    TYPE_INT = 4
    TYPE_FLOAT = 5
    TYPE_TEXT = 6

    TYPE_CHOICES = (
        (TYPE_STR, 'String'),
        (TYPE_IMAGE, 'Image'),
        (TYPE_BOOLEAN, 'Boolean'),
        (TYPE_INT, 'Integer'),
        (TYPE_FLOAT, 'Float'),
        (TYPE_TEXT, 'Text')
    )

    objects = GlobalPreferencesManager()

    key = models.CharField(max_length=50, unique=True,
                           validators=[RegexValidator(
                               regex='^[a-z\d]+[a-z\d_]*[a-z\d]+$',
                               message=_('Key should be in snake case'))])
    value = models.TextField(blank=True)
    display_name = models.CharField(max_length=255)
    image = models.ImageField(null=True, blank=True, upload_to=get_pref_img_dir)
    note = models.TextField(blank=True, null=True)

    # for dashboard to easily distinguish different types
    type = models.IntegerField(default=TYPE_STR, choices=TYPE_CHOICES)
    json_value = JSONField(blank=True, null=True)

    class Meta:
        db_table = 'configsetting_globalpreference'
        permissions = (('list_globalpreference', 'Can list globalpreference'),)

    def __str__(self):
        return self.key
