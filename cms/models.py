import os
from django.db import models
from django.utils import timezone


def image_directory(instance, filename):
    """
    :return: cms/example.com/home-page/content.jpg
    """
    upload_dir = os.path.join('cms', 'image')
    return os.path.join(upload_dir, filename)


class Website(models.Model):
    """
    Model for Categorizing which website is the page for
    """
    name = models.CharField(max_length=255, unique=True, default=None)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name


class AdPage(models.Model):
    # page = models.SlugField(max_length=50, default=None, null=True, blank=True)
    # website = models.ForeignKey(Website, null=True, blank=True,
    #                             on_delete=models.SET_NULL)
    header = models.TextField(null=True, blank=True)
    status = models.BooleanField(default=1)

    def __str__(self):
        return self.header

    def get_active_ads(self):
        return self.advertisements.filter(status=1).order_by('rank')


class Advertisement(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    rank = models.IntegerField(default=1, null=True, blank=True)
    ad_page = models.ForeignKey(AdPage, null=True, blank=True,
                                related_name='advertisements',
                                on_delete=models.SET_NULL)
    status = models.BooleanField(default=0)
    # left ads
    title = models.TextField(max_length=255, default=None,
                             null=True, blank=True)
    content = models.TextField(null=True, blank=True)
    image = models.ImageField(null=True, blank=True, upload_to=image_directory)
    img_url = models.URLField(max_length=200, null=True, blank=True)
    # right ads
    r_title = models.TextField(max_length=255, default=None,
                               null=True, blank=True)
    r_content = models.TextField(null=True, blank=True)
    r_image_0 = models.ImageField(null=True, blank=True, upload_to=image_directory)
    r_img_0_url = models.URLField(max_length=200, null=True, blank=True)
    r_image_1 = models.ImageField(null=True, blank=True, upload_to=image_directory)
    r_img_1_url = models.URLField(max_length=200, null=True, blank=True)
    r_image_2 = models.ImageField(null=True, blank=True, upload_to=image_directory)
    r_img_2_url = models.URLField(max_length=200, null=True, blank=True)
