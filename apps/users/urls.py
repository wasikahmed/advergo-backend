from django.urls import path
from rest_framework_simplejwt.views import TokenBlacklistView, TokenRefreshView

from .views import (
    GoogleLoginView,
    LoginView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PhoneOTPRequestView,
    PhoneOTPVerifyView,
    RegisterView,
    StaffInviteAcceptView,
    StaffInviteCreateView,
    TwoFactorVerifyView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("logout/", TokenBlacklistView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("2fa/verify/", TwoFactorVerifyView.as_view(), name="auth-2fa-verify"),
    path(
        "password-reset/request/",
        PasswordResetRequestView.as_view(),
        name="auth-password-reset-request",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("google/", GoogleLoginView.as_view(), name="auth-google"),
    path("phone/otp/request/", PhoneOTPRequestView.as_view(), name="auth-phone-otp-request"),
    path("phone/otp/verify/", PhoneOTPVerifyView.as_view(), name="auth-phone-otp-verify"),
    path("staff-invites/", StaffInviteCreateView.as_view(), name="auth-staff-invite-create"),
    path(
        "staff-invites/accept/", StaffInviteAcceptView.as_view(), name="auth-staff-invite-accept"
    ),
]
