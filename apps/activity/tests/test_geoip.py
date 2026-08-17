from types import SimpleNamespace
from unittest.mock import patch

import pytest

from apps.activity.geoip import resolve_location
from apps.activity.services import _describe_location

pytestmark = pytest.mark.django_db


def test_resolve_location_returns_empty_when_no_database(settings):
    from apps.activity.geoip import _reader

    _reader.cache_clear()
    settings.GEOIP_PATH = "/nonexistent/GeoLite2-City.mmdb"
    assert resolve_location("8.8.8.8") == ""
    _reader.cache_clear()


def test_resolve_location_formats_city_and_country():
    fake_response = SimpleNamespace(
        city=SimpleNamespace(name="Dhaka"), country=SimpleNamespace(name="Bangladesh")
    )
    fake_reader = SimpleNamespace(city=lambda ip: fake_response)

    with patch("apps.activity.geoip._reader", return_value=fake_reader):
        assert resolve_location("8.8.8.8") == "Dhaka, Bangladesh"


def test_resolve_location_handles_address_not_found():
    import geoip2.errors

    def raise_not_found(ip):
        raise geoip2.errors.AddressNotFoundError("not found")

    fake_reader = SimpleNamespace(city=raise_not_found)

    with patch("apps.activity.geoip._reader", return_value=fake_reader):
        assert resolve_location("10.0.0.1") == ""


def test_describe_location_calls_geoip_for_public_ip():
    with patch("apps.activity.geoip.resolve_location", return_value="Dhaka, Bangladesh") as mock:
        assert _describe_location("8.8.8.8") == "Dhaka, Bangladesh"
        mock.assert_called_once_with("8.8.8.8")


def test_describe_location_skips_geoip_for_private_ip():
    with patch("apps.activity.geoip.resolve_location") as mock:
        assert _describe_location("192.168.1.1") == "Local network"
        mock.assert_not_called()
