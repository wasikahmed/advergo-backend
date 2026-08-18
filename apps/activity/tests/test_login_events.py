import re
from unittest.mock import patch

import pytest
from django.core import mail
from django.test import Client
from rest_framework.test import APIClient

from apps.activity.models import LoginChannel, LoginEvent
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


# --- API password login ------------------------------------------------------


def test_customer_password_login_logs_success(api_client):
    UserFactory(email="cust1@example.com", password="Str0ngPassw0rd!", is_staff=False)
    response = api_client.post(
        "/api/v1/auth/login/", {"identifier": "cust1@example.com", "password": "Str0ngPassw0rd!"}
    )
    assert response.status_code == 200

    event = LoginEvent.objects.get()
    assert event.success is True
    assert event.channel == LoginChannel.API_PASSWORD
    assert event.user.email == "cust1@example.com"


def test_customer_password_login_logs_failure(api_client):
    UserFactory(email="cust2@example.com", password="Str0ngPassw0rd!", is_staff=False)
    response = api_client.post(
        "/api/v1/auth/login/", {"identifier": "cust2@example.com", "password": "WrongPassword!"}
    )
    assert response.status_code == 401

    event = LoginEvent.objects.get()
    assert event.success is False
    assert event.channel == LoginChannel.API_PASSWORD
    assert event.user is None
    assert event.identifier == "cust2@example.com"


def test_staff_password_login_only_logs_after_2fa_completes(api_client):
    UserFactory(email="staff1@example.com", password="Str0ngPassw0rd!", is_staff=True)
    login_response = api_client.post(
        "/api/v1/auth/login/", {"identifier": "staff1@example.com", "password": "Str0ngPassw0rd!"}
    )
    assert login_response.status_code == 202
    # Password matched, but the 2FA gate hasn't been passed yet -- no login
    # recorded as complete until it is.
    assert not LoginEvent.objects.exists()

    challenge_id = login_response.data["challengeId"]
    code = re.search(r"code is (\d{6})", mail.outbox[-1].body).group(1)
    verify_response = api_client.post(
        "/api/v1/auth/2fa/verify/", {"challengeId": challenge_id, "code": code}
    )
    assert verify_response.status_code == 200

    event = LoginEvent.objects.get()
    assert event.success is True
    assert event.user.email == "staff1@example.com"


def test_wrong_2fa_code_logs_failure(api_client):
    UserFactory(email="staff2@example.com", password="Str0ngPassw0rd!", is_staff=True)
    login_response = api_client.post(
        "/api/v1/auth/login/", {"identifier": "staff2@example.com", "password": "Str0ngPassw0rd!"}
    )
    challenge_id = login_response.data["challengeId"]

    api_client.post("/api/v1/auth/2fa/verify/", {"challengeId": challenge_id, "code": "000000"})

    event = LoginEvent.objects.get()
    assert event.success is False


# --- API Google login ---------------------------------------------------------


def test_customer_google_login_logs_success(api_client, settings):
    settings.GOOGLE_CLIENT_ID = "test-client-id"
    with patch("apps.users.google_auth.google_id_token.verify_oauth2_token") as verify:
        verify.return_value = {"email": "googlecust@example.com", "email_verified": True}
        response = api_client.post("/api/v1/auth/google/", {"idToken": "fake-valid-token"})
    assert response.status_code == 200

    event = LoginEvent.objects.get()
    assert event.success is True
    assert event.channel == LoginChannel.API_GOOGLE
    assert event.user.email == "googlecust@example.com"


def test_google_login_invalid_token_logs_failure(api_client, settings):
    settings.GOOGLE_CLIENT_ID = "test-client-id"
    with patch("apps.users.google_auth.google_id_token.verify_oauth2_token") as verify:
        verify.side_effect = ValueError("bad token")
        api_client.post("/api/v1/auth/google/", {"idToken": "fake-invalid-token"})

    event = LoginEvent.objects.get()
    assert event.success is False
    assert event.channel == LoginChannel.API_GOOGLE
    assert event.user is None


# --- Django admin session login -----------------------------------------------


def test_admin_password_login_only_logs_after_2fa_completes(settings):
    settings.ALLOWED_HOSTS = ["*"]
    admin = UserFactory(email="adminweb1@example.com", password="Str0ngPassw0rd!", is_staff=True)
    client = Client()

    response = client.post(
        "/admin/login/", {"username": "adminweb1@example.com", "password": "Str0ngPassw0rd!"}
    )
    assert response.status_code == 302
    # Django session exists now, but our own 2FA gate hasn't been passed --
    # no login event yet.
    assert not LoginEvent.objects.exists()

    # The OTP is only sent once the verify page is actually loaded (GET),
    # not at password-login time.
    client.get("/admin-2fa/verify/?next=/admin/")
    code = re.search(r"code is (\d{6})", mail.outbox[-1].body).group(1)
    verify_response = client.post("/admin-2fa/verify/?next=/admin/", {"code": code})
    assert verify_response.status_code == 302

    event = LoginEvent.objects.get()
    assert event.success is True
    assert event.channel == LoginChannel.ADMIN_PASSWORD
    assert event.user == admin


def test_admin_password_login_wrong_password_logs_failure(settings):
    settings.ALLOWED_HOSTS = ["*"]
    UserFactory(email="adminweb2@example.com", password="Str0ngPassw0rd!", is_staff=True)
    client = Client()

    client.post("/admin/login/", {"username": "adminweb2@example.com", "password": "WrongPass!"})

    event = LoginEvent.objects.get()
    assert event.success is False
    assert event.channel == LoginChannel.ADMIN_PASSWORD


def test_admin_2fa_wrong_code_logs_failure(settings):
    settings.ALLOWED_HOSTS = ["*"]
    UserFactory(email="adminweb3@example.com", password="Str0ngPassw0rd!", is_staff=True)
    client = Client()
    client.post(
        "/admin/login/", {"username": "adminweb3@example.com", "password": "Str0ngPassw0rd!"}
    )

    client.post("/admin-2fa/verify/?next=/admin/", {"code": "000000"})

    event = LoginEvent.objects.get()
    assert event.success is False
    assert event.channel == LoginChannel.ADMIN_PASSWORD


# --- Admin Google login --------------------------------------------------------


def test_admin_google_login_logs_success(settings):
    settings.GOOGLE_CLIENT_ID = "test-client-id"
    admin = UserFactory(email="admingoogle@example.com", is_staff=True)
    client = Client()

    with patch("apps.users.google_auth.google_id_token.verify_oauth2_token") as verify:
        verify.return_value = {"email": "admingoogle@example.com", "email_verified": True}
        client.post(
            "/admin-google-login/",
            data='{"id_token": "fake-token"}',
            content_type="application/json",
        )

    event = LoginEvent.objects.get()
    assert event.success is True
    assert event.channel == LoginChannel.ADMIN_GOOGLE
    assert event.user == admin


def test_admin_google_login_unmatched_account_logs_failure(settings):
    settings.GOOGLE_CLIENT_ID = "test-client-id"
    client = Client()

    with patch("apps.users.google_auth.google_id_token.verify_oauth2_token") as verify:
        verify.return_value = {"email": "notanadmin@example.com", "email_verified": True}
        client.post(
            "/admin-google-login/",
            data='{"id_token": "fake-token"}',
            content_type="application/json",
        )

    event = LoginEvent.objects.get()
    assert event.success is False
    assert event.channel == LoginChannel.ADMIN_GOOGLE
    assert event.identifier == "notanadmin@example.com"
