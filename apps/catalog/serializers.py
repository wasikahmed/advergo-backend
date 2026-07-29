from rest_framework import serializers

from .models import Fabric, Product, SizeChartRow, SportCategory


class SportCategorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="slug")

    class Meta:
        model = SportCategory
        fields = ["id", "name", "icon", "description"]


class FabricSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True, required=False, allow_null=True)

    class Meta:
        model = Fabric
        fields = ["id", "name", "grade", "best_for", "description", "image"]


class SizeChartRowSerializer(serializers.ModelSerializer):
    category_slug = serializers.CharField(source="category.slug", read_only=True, allow_null=True)

    class Meta:
        model = SizeChartRow
        fields = [
            "id",
            "category_slug",
            "size_label",
            "chest_in",
            "length_in",
            "shoulder_in",
            "sleeve_in",
        ]


class ProductSerializer(serializers.ModelSerializer):
    # Kept as the category's display name (not the slug) so it matches the
    # frontend's existing `Product.category: string` shape ("Football", etc.)
    # with zero changes needed on the UI side.
    category = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    image = serializers.ImageField(use_url=True, required=False, allow_null=True)
    # Decimal renders as a string by default (precision-safe); the frontend
    # type expects `rating: number`, and a 1-decimal star rating has no
    # precision to lose, so coerce it to a native JSON number here.
    rating = serializers.DecimalField(max_digits=2, decimal_places=1, coerce_to_string=False)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category",
            "category_slug",
            "price_range",
            "fabric",
            "rating",
            "review_count",
            "accent_color",
            "image",
            "is_featured",
        ]
