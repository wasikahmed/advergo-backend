import json
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _post(client, id_token="fake-token"):
    return client.post(
        reverse("admin-google-login"),
        data=json.dumps({"id_token": id_token}),
        content_type="application/json",
    )


def test_disabled_without_client_id(settings):
    settings.GOOGLE_CLIENT_ID = ""
    response = _post(Client())
    assert response.status_code == 503


def test_missing_token_is_a_bad_request(settings):
    settings.GOOGLE_CLIENT_ID = "test-client-id"
    response = Client().post(
        reverse("admin-google-login"), data=json.dumps({}), content_type="application/json"
    )
    assert response.status_code == 400


def test_invalid_google_token_is_rejected(settings):
    settings.GOOGLE_CLIENT_ID = "test-client-id"
    with patch("apps.users.google_auth.google_id_token.verify_oauth2_token") as verify:
        verify.side_effect = ValueError("bad token")
        response = _post(Client())
    assert response.status_code == 400


def test_verified_email_with_no_matching_staff_account_is_refused(settings):
    settings.GOOGLE_CLIENT_ID = "test-client-id"
    UserFactory(email="customer@example.com", is_staff=False)
    with patch("apps.users.google_auth.google_id_token.verify_oauth2_token") as verify:
        verify.return_value = {"email": "customer@example.com", "email_verified": True}
        response = _post(Client())
    assert response.status_code == 403


def test_unknown_email_is_refused(settings):
    settings.GOOGLE_CLIENT_ID = "test-client-id"
    with patch("apps.users.google_auth.google_id_token.verify_oauth2_token") as verify:
        verify.return_value = {"email": "nobody@example.com", "email_verified": True}
        response = _post(Client())
    assert response.status_code == 403


def test_matching_staff_account_logs_in_and_still_needs_2fa(settings):
    settings.GOOGLE_CLIENT_ID = "test-client-id"
    admin = UserFactory(email="staffgoogle@example.com", is_staff=True)
    client = Client()

    with patch("apps.users.google_auth.google_id_token.verify_oauth2_token") as verify:
        verify.return_value = {"email": "staffgoogle@example.com", "email_verified": True}
        response = _post(client)

    assert response.status_code == 200
    data = response.json()
    assert data["redirect"].startswith(reverse("admin-2fa-verify"))

    # Session is authenticated, but the 2FA checkpoint still gates the admin.
    admin_response = client.get("/admin/", follow=False)
    assert admin_response.status_code == 302
    assert "/admin-2fa/verify/" in admin_response.url


def test_inactive_staff_account_is_refused(settings):
    settings.GOOGLE_CLIENT_ID = "test-client-id"
    UserFactory(email="inactivestaff@example.com", is_staff=True, is_active=False)
    with patch("apps.users.google_auth.google_id_token.verify_oauth2_token") as verify:
        verify.return_value = {"email": "inactivestaff@example.com", "email_verified": True}
        response = _post(Client())
    assert response.status_code == 403
