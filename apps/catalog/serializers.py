from rest_framework import serializers

from .models import Category, Design, Fabric, FabricImage, Product, ProductImage, SizeChartRow


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
    images = serializers.SerializerMethodField()

    class Meta:
        model = Fabric
        fields = ["id", "name", "grade", "best_for", "description", "image", "images"]

    def get_images(self, obj):
        gallery = FabricImageSerializer(obj.images.all(), many=True, context=self.context).data
        if obj.image:
            return [{"id": f"legacy-{obj.pk}", "image": obj.image.url}] + gallery
        return gallery


class FabricImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True)

    class Meta:
        model = FabricImage
        fields = ["id", "image", "order"]


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


class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True)

    class Meta:
        model = ProductImage
        fields = ["id", "image", "order"]


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    image = serializers.ImageField(use_url=True, required=False, allow_null=True)
    images = serializers.SerializerMethodField()
    rating = serializers.DecimalField(max_digits=2, decimal_places=1, coerce_to_string=False)
    list_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False, allow_null=True
    )
    sale_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False, allow_null=True
    )
    discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, coerce_to_string=False
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category",
            "category_slug",
            "product_type",
            "age_group",
            "price_range",
            "list_price",
            "sale_price",
            "discount_percent",
            "fabric",
            "rating",
            "review_count",
            "accent_color",
            "image",
            "images",
            "is_featured",
        ]

    def get_images(self, obj):
        gallery = ProductImageSerializer(obj.images.all(), many=True, context=self.context).data
        if obj.image:
            return [{"id": f"legacy-{obj.pk}", "image": obj.image.url}] + gallery
        return gallery


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
