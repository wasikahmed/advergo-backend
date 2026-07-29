from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "email", "phone", "full_name", "password"]
        extra_kwargs = {"phone": {"required": False}}

    def validate(self, attrs):
        if not attrs.get("email") and not attrs.get("phone"):
            raise serializers.ValidationError("Provide an email or a phone number.")
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "phone", "full_name", "is_staff", "created_at"]
        read_only_fields = ["id", "email", "is_staff", "created_at"]


class EmailOrPhoneTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Accepts `identifier` (email or phone) instead of a fixed username field."""

    username_field = "identifier"
