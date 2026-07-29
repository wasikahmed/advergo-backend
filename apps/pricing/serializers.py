from rest_framework import serializers

from apps.catalog.models import Fabric, SportCategory


class PriceEstimateRequestSerializer(serializers.Serializer):
    fabric = serializers.PrimaryKeyRelatedField(
        queryset=Fabric.objects.all(), required=False, allow_null=True
    )
    category = serializers.SlugRelatedField(
        slug_field="slug", queryset=SportCategory.objects.all(), required=False, allow_null=True
    )
    quantity = serializers.IntegerField(min_value=1)


class PriceEstimateResponseSerializer(serializers.Serializer):
    unit_price_low = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit_price_high = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_low = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_high = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = serializers.DecimalField(max_digits=4, decimal_places=1)
