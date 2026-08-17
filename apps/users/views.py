import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.permissions import IsAdmin

from .invites import send_staff_invite_email
from .models import StaffInvite
from .otp import (
    OTPChannel,
    OTPPurpose,
    create_and_send_login_2fa_otp,
    create_otp,
    resend_otp,
    verify_otp,
)
from .password_reset import send_password_reset_email
from .serializers import (
    EmailOrPhoneTokenObtainPairSerializer,
    GoogleLoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PhoneOTPRequestSerializer,
    PhoneOTPVerifySerializer,
    ProfileSerializer,
    RegisterSerializer,
    StaffInviteAcceptSerializer,
    StaffInviteCreateSerializer,
    TwoFactorResendSerializer,
    TwoFactorVerifySerializer,
)
from .sms import SMSNotConfiguredError, send_sms_otp

User = get_user_model()


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class RegisterView(generics.CreateAPIView):
    """
    A normal signup, unless the email/phone already belongs to an inactive
    "shell" account (created earlier from a guest quote -- see
    apps.users.services.get_or_create_guest_user). In that case this isn't
    a new account at all, it's *their* existing history -- routed through
    the same secure "prove you own this email" flow as password reset
    instead of letting anyone claim it by simply typing a password.
    """

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get("email")
        phone = serializer.validated_data.get("phone")

        existing = None
        if email:
            existing = User.objects.filter(email__iexact=email).first()
        if existing is None and phone:
            existing = User.objects.filter(phone=phone).first()

        if existing is not None and existing.is_active:
            raise ValidationError(
                {"email": "An account with this email or phone already exists. Log in instead."}
            )

        if existing is not None:
            # Inactive shell. Phone-only shells can't be claimed yet --
            # phone OTP delivery isn't wired up to a real SMS provider.
            if not existing.email:
                return Response(
                    {
                        "detail": "An account already exists for this phone number. Phone "
                        "activation isn't available yet -- please contact support."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            send_password_reset_email(existing)
            return Response(
                {
                    "detail": "We found an existing account for this email. Check your inbox "
                    "for a link to activate it.",
                    "accountExists": True,
                },
                status=status.HTTP_200_OK,
            )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class LoginView(TokenObtainPairView):
    """
    Staff accounts don't get tokens directly: a valid password only unlocks
    an email-OTP challenge (see TwoFactorVerifyView). Non-staff accounts log
    in normally in one step.
    """

    serializer_class = EmailOrPhoneTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0]) from e

        user = serializer.user
        if user.is_staff:
            challenge_id = create_and_send_login_2fa_otp(user)
            return Response(
                {"twoFactorRequired": True, "challengeId": challenge_id},
                status=status.HTTP_202_ACCEPTED,
            )

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class TwoFactorVerifyView(generics.GenericAPIView):
    serializer_class = TwoFactorVerifySerializer
    permission_classes = [permissions.AllowAny]

    def get_throttles(self):
        self.throttle_scope = "otp_verify"
        return [ScopedRateThrottle()]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        otp = verify_otp(
            challenge_id=serializer.validated_data["challenge_id"],
            code=serializer.validated_data["code"],
            purpose=OTPPurpose.LOGIN_2FA,
        )
        if otp is None or otp.user_id is None:
            raise ValidationError({"code": "Invalid or expired code."})

        user = User.objects.get(pk=otp.user_id)
        return Response(_tokens_for_user(user), status=status.HTTP_200_OK)


class TwoFactorResendView(generics.GenericAPIView):
    """Re-sends the code for an in-progress LOGIN_2FA challenge -- shared by
    the login page and the staff-invite-accept page, both of which land on
    the same challenge/code flow after their first step succeeds."""

    serializer_class = TwoFactorResendSerializer
    permission_classes = [permissions.AllowAny]

    def get_throttles(self):
        self.throttle_scope = "otp_request"
        return [ScopedRateThrottle()]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sent = resend_otp(
            challenge_id=serializer.validated_data["challenge_id"], purpose=OTPPurpose.LOGIN_2FA
        )
        if not sent:
            raise ValidationError({"challengeId": "This challenge has expired. Please start over."})
        return Response({"detail": "Code resent."})


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [permissions.AllowAny]

    def get_throttles(self):
        self.throttle_scope = "password_reset"
        return [ScopedRateThrottle()]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Always 200, whether or not the email matches an account -- avoids
        # leaking which addresses have accounts.
        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        if user is not None:
            send_password_reset_email(user)

        return Response({"detail": "If that email exists, a reset link has been sent."})


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["new_password"])
        update_fields = ["password"]
        # Same link doubles as the "claim your account" flow for an
        # inactive shell (see RegisterView) -- proving email ownership and
        # setting a password *is* the activation moment there too.
        if not user.is_active:
            user.is_active = True
            update_fields.append("is_active")
        user.save(update_fields=update_fields)

        return Response({"detail": "Password updated."})


class GoogleLoginView(generics.GenericAPIView):
    """Verifies a Google ID token from the frontend and issues our own JWT,
    creating the account on first sign-in. Staff accounts still go through
    the email-OTP 2FA challenge, same as password login."""

    serializer_class = GoogleLoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        if not settings.GOOGLE_CLIENT_ID:
            return Response(
                {"detail": "Google sign-in isn't configured yet."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = google_id_token.verify_oauth2_token(
                serializer.validated_data["id_token"],
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except ValueError as e:
            raise ValidationError({"id_token": "Invalid Google token."}) from e

        email = payload.get("email")
        if not email or not payload.get("email_verified"):
            raise ValidationError({"id_token": "Google account has no verified email."})

        user, created = User.objects.get_or_create(
            email__iexact=email,
            defaults={
                "email": email,
                "full_name": payload.get("name", ""),
                "avatar_url": payload.get("picture", ""),
            },
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        else:
            # Matched an existing account -- possibly an inactive "shell"
            # created from a guest quote (see apps.users.services). Google
            # has already verified this person owns the email, so this
            # *is* the activation moment -- no separate claim step needed,
            # unlike the password-based register flow.
            update_fields = []
            if not user.is_active:
                user.is_active = True
                update_fields.append("is_active")
            if not user.full_name and payload.get("name"):
                user.full_name = payload["name"]
                update_fields.append("full_name")
            if payload.get("picture") and user.avatar_url != payload["picture"]:
                # Google's photo URL can change over time -- keep it fresh
                # on every login rather than only capturing it once.
                user.avatar_url = payload["picture"]
                update_fields.append("avatar_url")
            if update_fields:
                user.save(update_fields=update_fields)

        if user.is_staff:
            challenge_id = create_and_send_login_2fa_otp(user)
            return Response(
                {"twoFactorRequired": True, "challengeId": challenge_id},
                status=status.HTTP_202_ACCEPTED,
            )

        return Response(_tokens_for_user(user), status=status.HTTP_200_OK)


class PhoneOTPRequestView(generics.GenericAPIView):
    """Scaffolded for a future SMS provider -- always returns 503 until
    apps.users.sms.send_sms_otp is wired up to a real gateway."""

    serializer_class = PhoneOTPRequestSerializer
    permission_classes = [permissions.AllowAny]

    def get_throttles(self):
        self.throttle_scope = "otp_request"
        return [ScopedRateThrottle()]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]

        challenge_id, code = create_otp(
            identifier=phone, channel=OTPChannel.SMS, purpose=OTPPurpose.PHONE_VERIFY
        )
        try:
            send_sms_otp(phone, code)
        except SMSNotConfiguredError as e:
            return Response({"detail": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({"detail": "Verification code sent.", "challengeId": challenge_id})


class PhoneOTPVerifyView(generics.GenericAPIView):
    serializer_class = PhoneOTPVerifySerializer
    permission_classes = [permissions.AllowAny]

    def get_throttles(self):
        self.throttle_scope = "otp_verify"
        return [ScopedRateThrottle()]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        otp = verify_otp(
            challenge_id=serializer.validated_data["challenge_id"],
            code=serializer.validated_data["code"],
            purpose=OTPPurpose.PHONE_VERIFY,
        )
        if otp is None:
            raise ValidationError({"code": "Invalid or expired code."})

        user, _ = User.objects.get_or_create(phone=otp.identifier)
        return Response(_tokens_for_user(user), status=status.HTTP_200_OK)


class StaffInviteCreateView(generics.CreateAPIView):
    """Admin-only: invite an email address to a Group. No open self-serve
    staff registration endpoint exists -- this is the only way in."""

    queryset = StaffInvite.objects.all()
    serializer_class = StaffInviteCreateSerializer
    permission_classes = [IsAdmin]

    def perform_create(self, serializer):
        invite = serializer.save(
            invited_by=self.request.user,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + timedelta(days=7),
        )
        send_staff_invite_email(invite)


class StaffInviteAcceptView(generics.GenericAPIView):
    serializer_class = StaffInviteAcceptSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invite = serializer.invite

        user = User.objects.create_user(
            email=invite.email,
            password=serializer.validated_data["password"],
            full_name=serializer.validated_data["full_name"],
            is_staff=True,
        )
        user.groups.add(invite.group)

        invite.accepted_at = timezone.now()
        invite.save(update_fields=["accepted_at"])

        # Staff accounts always go through the 2FA challenge before getting
        # tokens (see LoginView) -- accepting an invite shouldn't be a
        # backdoor around that.
        challenge_id = create_and_send_login_2fa_otp(user)
        return Response(
            {"twoFactorRequired": True, "challengeId": challenge_id},
            status=status.HTTP_201_CREATED,
        )
