from rest_framework import serializers

from apps.catalog.models import Product
from apps.catalog.serializers import ProductSerializer

from .models import WishlistItem


class WishlistItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        source="product", queryset=Product.objects.all(), write_only=True
    )

    class Meta:
        model = WishlistItem
        fields = ["id", "product", "product_id", "created_at"]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        # DRF's automatic UniqueConstraint validator doesn't fire cleanly here
        # -- it keys off the model field name ("product"), but the writable
        # field is "product_id" (source="product"). Without this, a duplicate
        # surfaces as a raw 500 IntegrityError instead of a 400.
        if WishlistItem.objects.filter(
            user=validated_data["user"], product=validated_data["product"]
        ).exists():
            raise serializers.ValidationError({"product_id": "Already in your wishlist."})
        return super().create(validated_data)
