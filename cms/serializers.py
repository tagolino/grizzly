from rest_framework import serializers
from .models import Website, AdPage, Advertisement


class WebsiteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Website
        fields = '__all__'


class AdvertisementSerializer(serializers.ModelSerializer):

    class Meta:
        model = Advertisement
        fields = '__all__'


class AdvertisementMemberSerializer(serializers.ModelSerializer):

    class Meta:
        model = Advertisement
        fields = ('title', 'content',
                  'image', 'img_url',
                  'r_title', 'r_content',
                  'r_image_0', 'r_img_0_url',
                  'r_image_1', 'r_img_1_url',
                  'r_image_2', 'r_img_2_url',)


class AdPageSerializer(serializers.ModelSerializer):
    ads = AdvertisementSerializer(many=True, required=False)

    class Meta:
        model = AdPage
        fields = ('header', 'ads', 'id',)


class AdMemberPageSerializer(serializers.ModelSerializer):
    ads = AdvertisementMemberSerializer(many=True, source='get_active_ads')

    class Meta:
        model = AdPage
        fields = ('header', 'ads',)
