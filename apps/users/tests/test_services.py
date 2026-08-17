import pytest

from apps.users.models import User
from apps.users.services import get_or_create_guest_user
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_creates_inactive_unusable_password_shell_when_no_match():
    user = get_or_create_guest_user(email="new.lead@example.com", phone="+8801711111111")
    assert user.email == "new.lead@example.com"
    assert user.phone == "+8801711111111"
    assert user.is_active is False
    assert not user.has_usable_password()


def test_reuses_existing_account_by_email_instead_of_duplicating():
    existing = UserFactory(email="known@example.com")
    user = get_or_create_guest_user(email="known@example.com", phone="+8801722222222")
    assert user.id == existing.id
    assert User.objects.filter(email="known@example.com").count() == 1


def test_falls_back_to_phone_match_when_email_is_new():
    existing = UserFactory(email=None, phone="+8801733333333")
    user = get_or_create_guest_user(email="different@example.com", phone="+8801733333333")
    assert user.id == existing.id


def test_returns_none_without_email_or_phone():
    assert get_or_create_guest_user() is None
