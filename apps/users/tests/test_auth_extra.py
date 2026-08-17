import re
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import StaffInvite
from apps.users.otp import OTPPurpose
from apps.users.tests.factories import UserFactory
from apps.users.tests.helpers import login

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


# --- Admin 2FA ---------------------------------------------------------------


def test_staff_login_requires_2fa_challenge(api_client):
    UserFactory(email="admin@example.com", password="Str0ngPassw0rd!", is_staff=True)
    response = api_client.post(
        "/api/v1/auth/login/", {"identifier": "admin@example.com", "password": "Str0ngPassw0rd!"}
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.data["twoFactorRequired"] is True
    assert "access" not in response.data
    assert len(mail.outbox) == 1
    assert "verification code" in mail.outbox[0].body


def test_staff_login_completes_after_correct_otp(api_client):
    UserFactory(email="admin2@example.com", password="Str0ngPassw0rd!", is_staff=True)
    # The shared `login` helper already drives the full challenge+verify
    # flow -- assert it lands us authenticated.
    login(api_client, "admin2@example.com")
    response = api_client.get("/api/v1/auth/me/")
    assert response.status_code == status.HTTP_200_OK


def test_2fa_verify_rejects_wrong_code_but_leaves_challenge_valid(api_client):
    UserFactory(email="admin3@example.com", password="Str0ngPassw0rd!", is_staff=True)
    login_response = api_client.post(
        "/api/v1/auth/login/", {"identifier": "admin3@example.com", "password": "Str0ngPassw0rd!"}
    )
    challenge_id = login_response.data["challengeId"]

    wrong = api_client.post(
        "/api/v1/auth/2fa/verify/", {"challengeId": challenge_id, "code": "000000"}
    )
    assert wrong.status_code == status.HTTP_400_BAD_REQUEST

    # A mistyped code doesn't burn the user's only shot -- the real code
    # (read from the email, since only its hash is stored) still works.
    code = re.search(r"code is (\d{6})", mail.outbox[-1].body).group(1)
    right = api_client.post("/api/v1/auth/2fa/verify/", {"challengeId": challenge_id, "code": code})
    assert right.status_code == status.HTTP_200_OK


def test_2fa_code_cannot_be_reused(api_client):
    UserFactory(email="admin4@example.com", password="Str0ngPassw0rd!", is_staff=True)
    login_response = api_client.post(
        "/api/v1/auth/login/", {"identifier": "admin4@example.com", "password": "Str0ngPassw0rd!"}
    )
    challenge_id = login_response.data["challengeId"]
    code = re.search(r"code is (\d{6})", mail.outbox[-1].body).group(1)

    first = api_client.post("/api/v1/auth/2fa/verify/", {"challengeId": challenge_id, "code": code})
    assert first.status_code == status.HTTP_200_OK

    second = api_client.post(
        "/api/v1/auth/2fa/verify/", {"challengeId": challenge_id, "code": code}
    )
    assert second.status_code == status.HTTP_400_BAD_REQUEST


def test_2fa_resend_sends_a_new_code_that_verifies(api_client):
    UserFactory(email="admin7@example.com", password="Str0ngPassw0rd!", is_staff=True)
    login_response = api_client.post(
        "/api/v1/auth/login/", {"identifier": "admin7@example.com", "password": "Str0ngPassw0rd!"}
    )
    challenge_id = login_response.data["challengeId"]
    first_code = re.search(r"code is (\d{6})", mail.outbox[-1].body).group(1)

    resend = api_client.post("/api/v1/auth/2fa/resend/", {"challengeId": challenge_id})
    assert resend.status_code == status.HTTP_200_OK
    assert len(mail.outbox) == 2
    new_code = re.search(r"code is (\d{6})", mail.outbox[-1].body).group(1)
    assert new_code != first_code

    # The old code no longer works -- resend replaces it, doesn't add to it.
    stale = api_client.post(
        "/api/v1/auth/2fa/verify/", {"challengeId": challenge_id, "code": first_code}
    )
    assert stale.status_code == status.HTTP_400_BAD_REQUEST

    fresh = api_client.post(
        "/api/v1/auth/2fa/verify/", {"challengeId": challenge_id, "code": new_code}
    )
    assert fresh.status_code == status.HTTP_200_OK


def test_2fa_resend_rejects_unknown_challenge(api_client):
    response = api_client.post(
        "/api/v1/auth/2fa/resend/", {"challengeId": "00000000-0000-0000-0000-000000000000"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# --- Password reset ------------------------------------------------------------


def test_password_reset_request_sends_email_for_existing_user(api_client):
    UserFactory(email="reset@example.com", password="OldPassw0rd!")
    response = api_client.post(
        "/api/v1/auth/password-reset/request/", {"email": "reset@example.com"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(mail.outbox) == 1
    assert "reset-password" in mail.outbox[0].body


def test_password_reset_request_returns_200_for_unknown_email(api_client):
    response = api_client.post(
        "/api/v1/auth/password-reset/request/", {"email": "nobody@example.com"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(mail.outbox) == 0


def test_password_reset_confirm_sets_new_password(api_client):
    user = UserFactory(email="reset2@example.com", password="OldPassw0rd!")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    response = api_client.post(
        "/api/v1/auth/password-reset/confirm/",
        {"uid": uid, "token": token, "newPassword": "BrandNewPassw0rd!"},
    )
    assert response.status_code == status.HTTP_200_OK

    login_response = api_client.post(
        "/api/v1/auth/login/",
        {"identifier": "reset2@example.com", "password": "BrandNewPassw0rd!"},
    )
    assert login_response.status_code == status.HTTP_200_OK


def test_password_reset_confirm_rejects_bad_token(api_client):
    user = UserFactory(email="reset3@example.com", password="OldPassw0rd!")
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    response = api_client.post(
        "/api/v1/auth/password-reset/confirm/",
        {"uid": uid, "token": "not-a-real-token", "newPassword": "BrandNewPassw0rd!"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# --- Google login ---------------------------------------------------------------


def test_google_login_disabled_without_client_id(api_client, settings):
    settings.GOOGLE_CLIENT_ID = ""
    response = api_client.post("/api/v1/auth/google/", {"idToken": "whatever"})
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


def test_google_login_creates_user_from_verified_token(api_client, settings):
    settings.GOOGLE_CLIENT_ID = "test-client-id"
    with patch("apps.users.google_auth.google_id_token.verify_oauth2_token") as verify:
        verify.return_value = {
            "email": "googleuser@example.com",
            "email_verified": True,
            "name": "Google User",
        }
        response = api_client.post("/api/v1/auth/google/", {"idToken": "fake-valid-token"})

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data

    from apps.users.models import User

    user = User.objects.get(email="googleuser@example.com")
    assert user.full_name == "Google User"
    assert not user.has_usable_password()


def test_google_login_rejects_unverified_email(api_client, settings):
    settings.GOOGLE_CLIENT_ID = "test-client-id"
    with patch("apps.users.google_auth.google_id_token.verify_oauth2_token") as verify:
        verify.return_value = {"email": "unverified@example.com", "email_verified": False}
        response = api_client.post("/api/v1/auth/google/", {"idToken": "fake-token"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# --- Phone OTP scaffold (dormant) -----------------------------------------------


def test_phone_otp_request_returns_503_when_sms_not_configured(api_client):
    response = api_client.post("/api/v1/auth/phone/otp/request/", {"phone": "+8801700000001"})
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


def test_phone_otp_verify_logs_in_once_code_exists(api_client):
    # Simulates SMS having been sent by a future provider: create the
    # challenge directly (mirrors what PhoneOTPRequestView would do once a
    # real SMS gateway is wired up).
    from apps.users.otp import OTPChannel, create_otp

    challenge_id, code = create_otp(
        identifier="+8801700000002", channel=OTPChannel.SMS, purpose=OTPPurpose.PHONE_VERIFY
    )
    response = api_client.post(
        "/api/v1/auth/phone/otp/verify/", {"challengeId": challenge_id, "code": code}
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data

    from apps.users.models import User

    user = User.objects.get(phone="+8801700000002")
    assert user.email is None


# --- Staff invites ---------------------------------------------------------------


def test_non_admin_cannot_create_staff_invite(api_client):
    UserFactory(email="regular@example.com", password="Str0ngPassw0rd!")
    login(api_client, "regular@example.com")
    group = Group.objects.get_or_create(name="AccountsLimited")[0]
    response = api_client.post(
        "/api/v1/auth/staff-invites/", {"email": "newstaff@example.com", "group": group.id}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_can_invite_and_invitee_can_accept(api_client):
    UserFactory(email="admin5@example.com", password="Str0ngPassw0rd!", is_staff=True)
    login(api_client, "admin5@example.com")
    group = Group.objects.get_or_create(name="AccountsFull")[0]

    invite_response = api_client.post(
        "/api/v1/auth/staff-invites/", {"email": "newstaff2@example.com", "group": group.id}
    )
    assert invite_response.status_code == status.HTTP_201_CREATED
    assert len(mail.outbox) == 2  # 2FA code + invite email
    invite = StaffInvite.objects.get(email="newstaff2@example.com")

    accept_client = APIClient()
    accept_response = accept_client.post(
        "/api/v1/auth/staff-invites/accept/",
        {"token": invite.token, "fullName": "New Staffer", "password": "Str0ngPassw0rd!"},
    )
    assert accept_response.status_code == status.HTTP_201_CREATED
    assert accept_response.data["twoFactorRequired"] is True

    from apps.users.models import User

    new_user = User.objects.get(email="newstaff2@example.com")
    assert new_user.is_staff is True
    assert group in new_user.groups.all()


def test_staff_invite_cannot_be_accepted_twice(api_client):
    UserFactory(email="admin6@example.com", password="Str0ngPassw0rd!", is_staff=True)
    login(api_client, "admin6@example.com")
    group = Group.objects.get_or_create(name="AccountsLimited")[0]
    api_client.post(
        "/api/v1/auth/staff-invites/", {"email": "newstaff3@example.com", "group": group.id}
    )
    invite = StaffInvite.objects.get(email="newstaff3@example.com")

    accept_client = APIClient()
    first = accept_client.post(
        "/api/v1/auth/staff-invites/accept/",
        {"token": invite.token, "fullName": "First", "password": "Str0ngPassw0rd!"},
    )
    assert first.status_code == status.HTTP_201_CREATED

    second = accept_client.post(
        "/api/v1/auth/staff-invites/accept/",
        {"token": invite.token, "fullName": "Second", "password": "Str0ngPassw0rd!"},
    )
    assert second.status_code == status.HTTP_400_BAD_REQUEST
