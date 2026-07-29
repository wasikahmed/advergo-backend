from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import SportCategory
from apps.pricing.models import CategoryPriceRule

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_estimate_requires_quantity(api_client):
    response = api_client.post("/api/v1/pricing/estimate/", {})
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_estimate_rejects_zero_quantity(api_client):
    response = api_client.post("/api/v1/pricing/estimate/", {"quantity": 0})
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_estimate_works_with_only_quantity(api_client):
    response = api_client.post("/api/v1/pricing/estimate/", {"quantity": 25})
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "unitPriceLow" in body
    assert "totalLow" in body


def test_estimate_uses_category_slug(api_client):
    category = SportCategory.objects.create(slug="football", name="Football")
    CategoryPriceRule.objects.create(category=category, price_per_unit=Decimal("500.00"))

    response = api_client.post(
        "/api/v1/pricing/estimate/", {"category": "football", "quantity": 10}
    )
    assert response.status_code == status.HTTP_200_OK
    assert Decimal(response.json()["unitPriceLow"]) == Decimal("450.00")


def test_estimate_is_public_no_auth_required(api_client):
    response = api_client.post("/api/v1/pricing/estimate/", {"quantity": 5})
    assert response.status_code != status.HTTP_401_UNAUTHORIZED
