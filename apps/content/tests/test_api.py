from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.content.models import Banner, CompanyInfo, GalleryItem

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_active_banner_respects_date_range(api_client):
    now = timezone.now()
    Banner.objects.create(title="Expired", is_active=True, featured_to=now - timedelta(days=1))
    Banner.objects.create(title="Future", is_active=True, featured_from=now + timedelta(days=1))
    live = Banner.objects.create(title="Live now", is_active=True, priority=5)

    response = api_client.get("/api/v1/content/banners/active/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == live.title


def test_active_banner_returns_null_when_none_active(api_client):
    response = api_client.get("/api/v1/content/banners/active/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data is None


def test_active_banner_picks_highest_priority(api_client):
    Banner.objects.create(title="Low", is_active=True, priority=1)
    Banner.objects.create(title="High", is_active=True, priority=9)

    response = api_client.get("/api/v1/content/banners/active/")
    assert response.data["title"] == "High"


def test_gallery_filter_by_category(api_client):
    GalleryItem.objects.create(label="Sewing", category="factory")
    GalleryItem.objects.create(label="Delivery", category="clients")

    response = api_client.get("/api/v1/content/gallery/", {"category": "factory"})
    labels = {item["label"] for item in response.data}
    assert labels == {"Sewing"}


def test_gallery_item_exposes_src_not_image(api_client):
    GalleryItem.objects.create(label="Sewing", category="factory")
    response = api_client.get("/api/v1/content/gallery/")
    assert "src" in response.data[0]
    assert "image" not in response.data[0]


def test_company_info_is_created_lazily_and_readable(api_client):
    assert not CompanyInfo.objects.exists()
    response = api_client.get("/api/v1/content/company/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["name"]


def test_company_info_uses_camel_case_head_office(api_client):
    CompanyInfo.objects.create(pk=1, name="Advergo", head_office="Uttara, Dhaka")
    response = api_client.get("/api/v1/content/company/")
    assert response.json()["headOffice"] == "Uttara, Dhaka"


def test_anonymous_cannot_update_company_info(api_client):
    response = api_client.patch("/api/v1/content/company/", {"name": "Hacked"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
