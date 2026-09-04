from rest_framework import serializers

from .models import ProductReview, Review


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "name", "organization", "rating", "text"]


class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "name", "organization", "rating", "text"]

    def create(self, validated_data):
        # Public submissions always start pending -- admin moderates via /admin/.
        validated_data["status"] = Review._meta.get_field("status").default
        return super().create(validated_data)


class ProductReviewSerializer(serializers.ModelSerializer):
    reviewerName = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = ProductReview
        fields = ["id", "reviewerName", "rating", "text", "created_at"]


class ProductReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductReview
        fields = ["id", "product", "rating", "text"]

    def validate(self, attrs):
        request = self.context["request"]
        if ProductReview.objects.filter(user=request.user, product=attrs["product"]).exists():
            raise serializers.ValidationError({"product": "You've already reviewed this product."})
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        # Logged-in submissions still start pending -- admin moderates via /admin/.
        validated_data["status"] = ProductReview._meta.get_field("status").default
        return super().create(validated_data)
