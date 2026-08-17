from rest_framework import serializers

from apps.catalog.models import Category
from apps.core.utils import generate_reference_code
from apps.pricing.services import estimate_price
from apps.users.services import get_or_create_guest_user

from .models import QuoteRequest


class QuoteRequestCreateSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = QuoteRequest
        fields = [
            "id",
            "reference_code",
            "name",
            "phone",
            "email",
            "category",
            "product",
            "fabric",
            "design",
            "quantity",
            "size_breakdown",
            "delivery_address",
            "design_file",
            "notes",
            "estimated_price_low",
            "estimated_price_high",
        ]
        read_only_fields = ["id", "reference_code", "estimated_price_low", "estimated_price_high"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request is not None and request.user.is_authenticated:
            validated_data["user"] = request.user
        else:
            # Guest submission -- attach it to an existing account if the
            # email/phone matches one, otherwise create an inactive shell so
            # this quote (and everything that follows from it) has an
            # account to hang off of from day one.
            validated_data["user"] = get_or_create_guest_user(
                email=validated_data.get("email", ""), phone=validated_data.get("phone", "")
            )

        estimate = estimate_price(
            fabric=validated_data.get("fabric"),
            category=validated_data.get("category"),
            quantity=validated_data["quantity"],
        )
        validated_data["estimated_price_low"] = estimate.unit_price_low * validated_data["quantity"]
        validated_data["estimated_price_high"] = (
            estimate.unit_price_high * validated_data["quantity"]
        )
        validated_data["reference_code"] = generate_reference_code("QR")

        return super().create(validated_data)


class QuoteRequestAdminSerializer(serializers.ModelSerializer):
    """Full view for staff: adds status/admin_notes and read-friendly labels."""

    product_name = serializers.CharField(source="product.name", read_only=True, default=None)
    fabric_name = serializers.CharField(source="fabric.name", read_only=True, default=None)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = QuoteRequest
        fields = [
            "id",
            "reference_code",
            "user",
            "name",
            "phone",
            "email",
            "category",
            "category_name",
            "product",
            "product_name",
            "fabric",
            "fabric_name",
            "design",
            "quantity",
            "size_breakdown",
            "delivery_address",
            "design_file",
            "notes",
            "estimated_price_low",
            "estimated_price_high",
            "quoted_price",
            "status",
            "admin_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference_code",
            "user",
            "name",
            "phone",
            "email",
            "category",
            "product",
            "fabric",
            "design",
            "quantity",
            "size_breakdown",
            "delivery_address",
            "design_file",
            "notes",
            "estimated_price_low",
            "estimated_price_high",
            "created_at",
            "updated_at",
        ]
