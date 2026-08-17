import pytest

from apps.activity.services import _describe_device, _describe_location

pytestmark = pytest.mark.django_db


IPHONE_SAFARI = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
)
MAC_CHROME = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def test_describe_device_mobile_uses_device_family():
    assert _describe_device(IPHONE_SAFARI) == "Mobile Safari on iPhone"


def test_describe_device_desktop_uses_os_family():
    assert _describe_device(MAC_CHROME) == "Chrome on Mac"


def test_describe_device_empty_string_for_no_user_agent():
    assert _describe_device("") == ""


def test_describe_location_private_ip():
    assert _describe_location("192.168.1.5") == "Local network"


def test_describe_location_loopback():
    assert _describe_location("127.0.0.1") == "Local network"


def test_describe_location_public_ip_is_unresolved_for_now():
    assert _describe_location("8.8.8.8") == ""


def test_describe_location_none():
    assert _describe_location(None) == ""
