import pytest
from django.test import Client
from django.urls import reverse

from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _admin_login(client, email, password):
    return client.post(reverse("admin:login"), {"username": email, "password": password})


def test_admin_login_locks_out_after_repeated_failures(settings):
    # AXES_FAILURE_LIMIT = 5 -- the Nth failure itself is the one that trips
    # the lock (axes counts it before responding), so the limit-th attempt
    # already comes back 429, not the (limit + 1)th.
    admin = UserFactory(email="lockout@example.com", is_staff=True, password="Str0ngPassw0rd!")
    client = Client()

    for _ in range(settings.AXES_FAILURE_LIMIT - 1):
        response = _admin_login(client, admin.email, "wrong-password")
        assert response.status_code == 200  # re-rendered login form, not authenticated

    tripping_response = _admin_login(client, admin.email, "wrong-password")
    assert tripping_response.status_code == 429

    # Locked out now -- even the *correct* password is rejected outright.
    locked_out_response = _admin_login(client, admin.email, "Str0ngPassw0rd!")
    assert locked_out_response.status_code == 429
    assert client.session.get("_auth_user_id") is None


def test_admin_login_succeeds_under_the_failure_limit():
    admin = UserFactory(email="notlockedout@example.com", is_staff=True, password="Str0ngPassw0rd!")
    client = Client()

    for _ in range(3):
        _admin_login(client, admin.email, "wrong-password")

    _admin_login(client, admin.email, "Str0ngPassw0rd!")

    assert str(client.session.get("_auth_user_id")) == str(admin.pk)


def test_axes_does_not_gate_api_login(settings):
    # AXES_ONLY_ADMIN_SITE = True -- API login has its own DRF throttle
    # scopes and shouldn't also get locked out by axes after repeated
    # failures against the admin's separate failure counter.
    from rest_framework.test import APIClient

    from apps.users.tests.helpers import login

    admin = UserFactory(email="apinotlocked@example.com", is_staff=True, password="Str0ngPassw0rd!")
    api_client = APIClient()

    for _ in range(settings.AXES_FAILURE_LIMIT + 2):
        api_client.post(
            "/api/v1/auth/login/", {"identifier": admin.email, "password": "wrong-password"}
        )

    response = login(api_client, admin.email, "Str0ngPassw0rd!")
    assert response.status_code == 200
