from rest_framework import serializers

from .models import Category, Design, Fabric, Product, SizeChartRow


class CategorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="slug")
    image = serializers.ImageField(use_url=True, required=False, allow_null=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "image", "description", "is_featured", "children"]

    def get_children(self, obj):
        # One level is all the product/UX currently needs (no sub-subcategories);
        # avoids an extra query per row since `children` is prefetched by the view.
        return CategorySerializer(obj.children.all(), many=True, context=self.context).data


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
            "age_group",
            "size_label",
            "chest_in",
            "length_in",
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
    image = serializers.ImageField(use_url=True)

    class Meta:
        model = Design
        fields = [
            "id",
            "category",
            "name",
            "code",
            "image",
            "is_active",
            "created_at",
        ]
