import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import Category, Fabric, Product

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def football():
    return Category.objects.create(slug="football", name="Football")


@pytest.fixture
def cricket():
    return Category.objects.create(slug="cricket", name="Cricket")


def test_list_categories(api_client, football, cricket):
    response = api_client.get("/api/v1/catalog/categories/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2


def test_list_products_excludes_inactive_and_deleted(api_client, football):
    Product.objects.create(name="Active", category=football, is_active=True)
    inactive = Product.objects.create(name="Inactive", category=football, is_active=False)
    deleted = Product.objects.create(name="Deleted", category=football)
    deleted.delete()  # soft delete

    response = api_client.get("/api/v1/catalog/products/")
    names = {p["name"] for p in response.data}
    assert names == {"Active"}
    assert inactive.name not in names


def test_product_category_field_is_display_name_not_slug(api_client, football):
    Product.objects.create(name="Jersey", category=football)
    response = api_client.get("/api/v1/catalog/products/")
    product = response.json()[0]
    assert product["category"] == "Football"
    assert product["categorySlug"] == "football"


def test_filter_products_by_category(api_client, football, cricket):
    Product.objects.create(name="Jersey", category=football)
    Product.objects.create(name="Playing Shirt", category=cricket)

    response = api_client.get("/api/v1/catalog/products/", {"category": "cricket"})
    names = {p["name"] for p in response.data}
    assert names == {"Playing Shirt"}


def test_fabric_list_uses_camel_case_best_for(api_client):
    Fabric.objects.create(
        name="Pin Mesh", grade="Premium", best_for="Football", description="Light"
    )
    response = api_client.get("/api/v1/catalog/fabrics/")
    assert response.json()[0]["bestFor"] == "Football"


def test_anonymous_cannot_create_product(api_client, football):
    response = api_client.post(
        "/api/v1/catalog/products/", {"name": "Hack", "category": football.slug}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
