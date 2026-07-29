from rest_framework import serializers

from .models import Achievement, Banner, ClientLogo, CompanyInfo, GalleryItem, ProcessStep, Stat


class BannerSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True, required=False, allow_null=True)

    class Meta:
        model = Banner
        fields = ["id", "title", "subtitle", "image", "cta_label", "cta_href"]


class StatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stat
        fields = ["id", "value", "label"]


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = ["id", "icon", "title", "year", "issuing_body"]


class ClientLogoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientLogo
        fields = ["id", "name", "logo_url"]


class ProcessStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessStep
        fields = ["id", "number", "title", "description", "emoji"]


class GalleryItemSerializer(serializers.ModelSerializer):
    src = serializers.ImageField(source="image", use_url=True, required=False, allow_null=True)

    class Meta:
        model = GalleryItem
        fields = ["id", "src", "label", "category", "description"]


class CompanyInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyInfo
        fields = [
            "name",
            "tagline",
            "phone",
            "email",
            "email_alt",
            "website",
            "head_office",
            "factory",
            "founded",
            "md",
            "chairman",
        ]
