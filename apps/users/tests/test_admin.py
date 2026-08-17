from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.core import mail
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.users.admin_2fa import SESSION_VERIFIED_KEY
from apps.users.models import StaffInvite
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client():
    """Django admin session client, staff 2FA already satisfied -- these tests
    are about the StaffInvite admin's own permission logic, not the 2FA gate
    itself (covered separately in test_auth_extra.py)."""
    admin = UserFactory(email="siteadmin@example.com", is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(admin)
    session = client.session
    session[SESSION_VERIFIED_KEY] = True
    session.save()
    return client, admin


@pytest.fixture
def group():
    return Group.objects.get_or_create(name="AccountsLimited")[0]


def _make_invite(group, admin, accepted=False):
    return StaffInvite.objects.create(
        email="invitee@example.com",
        group=group,
        invited_by=admin,
        token="tok",
        expires_at=timezone.now() + timedelta(days=7),
        accepted_at=timezone.now() if accepted else None,
    )


def test_pending_invite_is_editable_in_admin(admin_client, group):
    client, admin = admin_client
    invite = _make_invite(group, admin, accepted=False)

    url = reverse("admin:users_staffinvite_change", args=[invite.id])
    response = client.get(url)

    assert response.status_code == 200
    assert b"Change staff invite" in response.content or response.context["title"] == "Change staff invite"


def test_accepted_invite_is_read_only_in_admin(admin_client, group):
    client, admin = admin_client
    invite = _make_invite(group, admin, accepted=True)

    url = reverse("admin:users_staffinvite_change", args=[invite.id])
    response = client.get(url)

    assert response.status_code == 200
    assert response.context["title"] == "View staff invite"


def test_accepted_invite_cannot_be_saved(admin_client, group):
    client, admin = admin_client
    invite = _make_invite(group, admin, accepted=True)

    url = reverse("admin:users_staffinvite_change", args=[invite.id])
    response = client.post(url, {"email": "changed@example.com", "group": group.id})

    # Read-only object -- POST is refused outright, not silently accepted.
    assert response.status_code == 403
    invite.refresh_from_db()
    assert invite.email == "invitee@example.com"


def test_accepted_invite_cannot_be_deleted(admin_client, group):
    client, admin = admin_client
    invite = _make_invite(group, admin, accepted=True)

    url = reverse("admin:users_staffinvite_delete", args=[invite.id])
    response = client.post(url, {"post": "yes"})

    assert response.status_code == 403
    assert StaffInvite.objects.filter(pk=invite.pk).exists()


def test_pending_invite_can_be_deleted(admin_client, group):
    client, admin = admin_client
    invite = _make_invite(group, admin, accepted=False)

    url = reverse("admin:users_staffinvite_delete", args=[invite.id])
    response = client.post(url, {"post": "yes"})

    assert response.status_code == 302
    assert not StaffInvite.objects.filter(pk=invite.pk).exists()


def test_resend_row_action_resends_pending_invite(admin_client, group, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    client, admin = admin_client
    invite = _make_invite(group, admin, accepted=False)
    old_token = invite.token
    mail.outbox = []

    url = reverse("admin:users_staffinvite_resend_invite_row", args=[invite.id])
    response = client.get(url)

    assert response.status_code == 302
    invite.refresh_from_db()
    assert invite.token != old_token
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [invite.email]


def test_resend_row_action_skips_accepted_invite(admin_client, group, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    client, admin = admin_client
    invite = _make_invite(group, admin, accepted=True)
    old_token = invite.token
    mail.outbox = []

    url = reverse("admin:users_staffinvite_resend_invite_row", args=[invite.id])
    response = client.get(url)

    assert response.status_code == 302
    invite.refresh_from_db()
    assert invite.token == old_token
    assert len(mail.outbox) == 0


def test_get_full_name_returns_full_name_field():
    user = UserFactory(full_name="Jane Doe")
    assert user.get_full_name() == "Jane Doe"
    assert user.get_short_name() == "Jane Doe"


def test_user_changelist_shows_avatar_chip(admin_client):
    client, admin = admin_client
    UserFactory(full_name="Chip Person", email="chip@example.com")

    response = client.get(reverse("admin:users_user_changelist"))

    assert response.status_code == 200
    assert "Chip Person" in response.content.decode()
