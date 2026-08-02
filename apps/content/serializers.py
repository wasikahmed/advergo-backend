from rest_framework import serializers

from .models import (
    Achievement,
    BankAccount,
    Banner,
    ClientLogo,
    CompanyInfo,
    GalleryCategory,
    GalleryItem,
    MobileBankingAgent,
    ProcessStep,
    Stat,
    TeamMember,
)


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
    image = serializers.ImageField(use_url=True, required=False, allow_null=True)

    class Meta:
        model = Achievement
        fields = ["id", "kind", "image", "title", "year", "issuing_body"]


class ClientLogoSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()

    class Meta:
        model = ClientLogo
        fields = ["id", "name", "logo", "logo_url"]

    def get_logo(self, obj):
        if not obj.logo:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.logo) if request else obj.logo


class ProcessStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessStep
        fields = ["id", "number", "title", "description", "emoji"]


class GalleryCategorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="slug")

    class Meta:
        model = GalleryCategory
        fields = ["id", "name", "icon"]


class GalleryItemSerializer(serializers.ModelSerializer):
    src = serializers.ImageField(source="image", use_url=True, required=False, allow_null=True)
    # Kept as the category's slug (not a display name) since these are the
    # same "factory"/"clients" values the field already held pre-FK, so no
    # frontend change is required to keep reading/filtering by this field.
    category = serializers.CharField(source="category.slug", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = GalleryItem
        fields = ["id", "src", "label", "category", "category_name", "description"]


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
            "trade_license_no",
            "about",
            "mission",
            "vision",
        ]


class TeamMemberSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(use_url=True, required=False, allow_null=True)

    class Meta:
        model = TeamMember
        fields = ["id", "name", "role", "photo", "bio", "is_leadership"]


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = [
            "id",
            "bank_name",
            "account_name",
            "account_number",
            "routing_number",
            "branch_name",
            "swift_code",
        ]


class MobileBankingAgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileBankingAgent
        fields = ["id", "provider", "agent_number", "label"]
