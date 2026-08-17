from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import StaffInvite

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "email", "phone", "full_name", "password"]
        # validators=[] on both: disables DRF's auto-added UniqueValidator
        # (which would reject before the view even runs) -- RegisterView
        # does its own uniqueness check, since an email/phone match against
        # an inactive shell account isn't a plain rejection, it's routed
        # into the claim-account flow instead.
        extra_kwargs = {
            "phone": {"required": False, "validators": []},
            "email": {"validators": []},
        }

    def validate(self, attrs):
        if not attrs.get("email") and not attrs.get("phone"):
            raise serializers.ValidationError("Provide an email or a phone number.")
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "phone", "full_name", "avatar_url", "is_staff", "created_at"]
        read_only_fields = ["id", "email", "is_staff", "created_at"]


class EmailOrPhoneTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Accepts `identifier` (email or phone) instead of a fixed username field."""

    username_field = "identifier"


class TwoFactorVerifySerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    code = serializers.CharField(max_length=8)


class TwoFactorResendSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate(self, attrs):
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(attrs["uid"])))
        except (User.DoesNotExist, ValueError, TypeError, OverflowError) as e:
            raise serializers.ValidationError({"uid": "Invalid reset link."}) from e

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"token": "Invalid or expired reset link."})

        attrs["user"] = user
        return attrs


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class PhoneOTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)


class PhoneOTPVerifySerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    code = serializers.CharField(max_length=8)


class StaffInviteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffInvite
        fields = ["id", "email", "group", "expires_at", "accepted_at", "created_at"]
        read_only_fields = ["id", "expires_at", "accepted_at", "created_at"]


class StaffInviteAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()
    full_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_token(self, value):
        try:
            invite = StaffInvite.objects.get(token=value)
        except StaffInvite.DoesNotExist as e:
            raise serializers.ValidationError("Invalid invite link.") from e
        if not invite.is_valid:
            raise serializers.ValidationError("This invite has expired or was already used.")
        if User.objects.filter(email__iexact=invite.email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        self.invite = invite
        return value
