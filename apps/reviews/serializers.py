from rest_framework import serializers

from .models import Review


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
