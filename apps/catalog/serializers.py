from rest_framework import serializers

from .models import Category, CategoryFilterOption, Design, Fabric, Product, SizeChartRow


class CategoryFilterOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryFilterOption
        fields = ["id", "value", "label"]


class CategorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="slug")
    filter_options = CategoryFilterOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "icon", "description", "filter_options"]


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


class DesignSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field="slug", queryset=Category.objects.all())
    filter_option = serializers.PrimaryKeyRelatedField(
        queryset=CategoryFilterOption.objects.all(), required=False, allow_null=True
    )
    filter_value = serializers.CharField(source="filter_option.value", read_only=True, default=None)
    image = serializers.ImageField(use_url=True)

    class Meta:
        model = Design
        fields = [
            "id",
            "category",
            "filter_option",
            "filter_value",
            "name",
            "code",
            "image",
            "is_active",
            "created_at",
        ]

    def validate(self, attrs):
        category = attrs.get("category", getattr(self.instance, "category", None))
        filter_option = attrs.get("filter_option", getattr(self.instance, "filter_option", None))
        if filter_option and category and filter_option.category_id != category.id:
            raise serializers.ValidationError(
                {"filter_option": "Must belong to the selected category."}
            )
        return attrs
