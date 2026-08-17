import pytest

from apps.core.admin_utils import user_chip
from apps.users.models import User
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_user_chip_renders_full_name():
    user = UserFactory(full_name="Jane Doe")
    html = user_chip(user)
    assert "Jane Doe" in html


def test_user_chip_falls_back_to_username_without_full_name():
    user = UserFactory(full_name="", email="noname@example.com")
    html = user_chip(user)
    assert "noname@example.com" in html


def test_user_chip_renders_em_dash_for_none():
    assert "&mdash;" in user_chip(None)


def test_user_chip_handles_phone_only_user_without_crashing():
    # Regression: phone-only accounts have email=None, so get_username()
    # (which returns USERNAME_FIELD="email") is None too -- naive `.0`
    # string-indexing on that in the template used to raise
    # VariableDoesNotExist instead of falling back gracefully.
    user = User(full_name="", email=None, phone="+8801234567890")
    html = user_chip(user)
    assert "+8801234567890" in html
