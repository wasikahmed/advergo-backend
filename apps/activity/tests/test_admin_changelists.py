import pytest
from django.test import Client
from django.urls import reverse

from apps.activity.models import ActivityLog, LoginChannel, LoginEvent
from apps.users.admin_2fa import SESSION_VERIFIED_KEY
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client():
    staff = UserFactory(email="siteadmin@example.com", is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(staff)
    session = client.session
    session[SESSION_VERIFIED_KEY] = True
    session.save()
    return client, staff


def test_login_event_changelist_shows_avatar_chip(admin_client):
    client, staff = admin_client
    actor = UserFactory(full_name="Login Chip Person")
    LoginEvent.objects.create(
        user=actor,
        identifier="loginchip@example.com",
        channel=LoginChannel.ADMIN_PASSWORD,
        success=True,
    )

    response = client.get(reverse("admin:activity_loginevent_changelist"))

    assert response.status_code == 200
    assert "Login Chip Person" in response.content.decode()


def test_activity_log_changelist_shows_avatar_chip(admin_client):
    client, staff = admin_client
    actor = UserFactory(full_name="Activity Chip Person")
    ActivityLog.objects.create(actor=actor, verb="created", object_repr="Something")

    response = client.get(reverse("admin:activity_activitylog_changelist"))

    assert response.status_code == 200
    assert "Activity Chip Person" in response.content.decode()
