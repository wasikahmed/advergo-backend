import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from apps.users.admin_2fa import SESSION_VERIFIED_KEY
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_client():
    staff = UserFactory(
        email="profileowner@example.com", full_name="Original Name", is_staff=True, is_superuser=False
    )
    client = Client()
    client.force_login(staff)
    session = client.session
    session[SESSION_VERIFIED_KEY] = True
    session.save()
    return client, staff


def test_anonymous_is_redirected_to_login():
    response = Client().get(reverse("admin-profile"))
    assert response.status_code == 302
    assert "login" in response.url


def test_non_staff_user_is_redirected_away(settings):
    settings.ALLOWED_HOSTS = ["*"]
    user = UserFactory(email="customer@example.com", is_staff=False)
    client = Client()
    client.force_login(user)
    response = client.get(reverse("admin-profile"))
    assert response.status_code == 302
    assert response.url == reverse("admin:index")


def test_staff_can_view_own_profile_form(staff_client, settings):
    client, staff = staff_client
    settings.ALLOWED_HOSTS = ["*"]
    response = client.get(reverse("admin-profile"))
    assert response.status_code == 200
    assert "Original Name" in response.content.decode()


def test_staff_can_update_name_and_phone(staff_client, settings):
    client, staff = staff_client
    settings.ALLOWED_HOSTS = ["*"]

    response = client.post(
        reverse("admin-profile"), {"full_name": "Updated Name", "phone": "+8801711111111"}
    )
    assert response.status_code == 302

    staff.refresh_from_db()
    assert staff.full_name == "Updated Name"
    assert staff.phone == "+8801711111111"


def test_staff_can_upload_an_avatar(staff_client, settings):
    client, staff = staff_client
    settings.ALLOWED_HOSTS = ["*"]

    image = SimpleUploadedFile(
        "avatar.gif", b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
        content_type="image/gif",
    )
    response = client.post(
        reverse("admin-profile"),
        {"full_name": staff.full_name, "phone": "", "avatar": image},
    )
    assert response.status_code == 302

    staff.refresh_from_db()
    assert staff.avatar
    assert "advergo/avatars/" in staff.avatar.name


def test_profile_form_cannot_grant_staff_or_superuser(staff_client, settings):
    """The form only ever exposes full_name/phone/avatar -- posting extra
    fields must be silently ignored, not raise or apply them."""
    client, staff = staff_client
    settings.ALLOWED_HOSTS = ["*"]
    assert not staff.is_superuser

    client.post(
        reverse("admin-profile"),
        {"full_name": staff.full_name, "phone": "", "is_superuser": "on", "is_staff": "on"},
    )

    staff.refresh_from_db()
    assert not staff.is_superuser
