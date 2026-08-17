import re
from unittest.mock import patch

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User
from apps.users.services import get_or_create_guest_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_register_with_active_email_is_rejected(api_client):
    from apps.users.tests.factories import UserFactory

    UserFactory(email="taken@example.com")
    response = api_client.post(
        "/api/v1/auth/register/", {"email": "taken@example.com", "password": "Str0ngPassw0rd!"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_register_with_email_shell_account_sends_claim_link_instead_of_creating(api_client):
    shell = get_or_create_guest_user(email="lead@example.com", phone="+8801711111111")
    mail.outbox = []

    response = api_client.post(
        "/api/v1/auth/register/", {"email": "lead@example.com", "password": "Str0ngPassw0rd!"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["accountExists"] is True
    assert User.objects.filter(email__iexact="lead@example.com").count() == 1
    assert len(mail.outbox) == 1
    assert "reset" in mail.outbox[0].subject.lower()

    shell.refresh_from_db()
    assert shell.is_active is False  # not activated yet -- only the link was sent


def test_register_with_phone_only_shell_is_told_to_contact_support(api_client):
    get_or_create_guest_user(phone="+8801722222222")
    mail.outbox = []

    response = api_client.post(
        "/api/v1/auth/register/", {"phone": "+8801722222222", "password": "Str0ngPassw0rd!"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert len(mail.outbox) == 0


def test_confirming_password_reset_activates_a_shell_account(api_client):
    shell = get_or_create_guest_user(email="activate.me@example.com")
    assert shell.is_active is False

    uid = urlsafe_base64_encode(force_bytes(shell.pk))
    token = default_token_generator.make_token(shell)

    response = api_client.post(
        "/api/v1/auth/password-reset/confirm/",
        {"uid": uid, "token": token, "newPassword": "Str0ngPassw0rd!"},
    )

    assert response.status_code == status.HTTP_200_OK
    shell.refresh_from_db()
    assert shell.is_active is True
    assert shell.check_password("Str0ngPassw0rd!")


def test_google_login_activates_and_backfills_a_shell_account(api_client, settings):
    settings.GOOGLE_CLIENT_ID = "test-client-id"
    shell = get_or_create_guest_user(email="google.lead@example.com")
    assert shell.is_active is False
    assert shell.full_name == ""

    with patch("apps.users.google_auth.google_id_token.verify_oauth2_token") as verify:
        verify.return_value = {
            "email": "google.lead@example.com",
            "email_verified": True,
            "name": "Google Lead",
            "picture": "https://example.com/photo.jpg",
        }
        response = api_client.post("/api/v1/auth/google/", {"idToken": "fake-token"})

    assert response.status_code == status.HTTP_200_OK
    shell.refresh_from_db()
    assert shell.is_active is True
    assert shell.full_name == "Google Lead"
    assert shell.avatar_url == "https://example.com/photo.jpg"
