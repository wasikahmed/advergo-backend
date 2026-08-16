import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import Category, Product
from apps.users.tests.factories import UserFactory
from apps.users.tests.helpers import login
from apps.wishlist.models import WishlistItem

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def product():
    category = Category.objects.create(slug="football", name="Football")
    return Product.objects.create(name="Tournament Jersey", category=category)


def test_anonymous_cannot_use_wishlist(api_client, product):
    response = api_client.get("/api/v1/wishlist/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_toggle_adds_then_removes(api_client, product):
    user = UserFactory(email="me@example.com", password="Str0ngPassw0rd!")
    login(api_client, user.email)

    first = api_client.post("/api/v1/wishlist/toggle/", {"product": product.id})
    assert first.status_code == status.HTTP_201_CREATED
    assert first.json()["wishlisted"] is True
    assert WishlistItem.objects.filter(user=user, product=product).exists()

    second = api_client.post("/api/v1/wishlist/toggle/", {"product": product.id})
    assert second.status_code == status.HTTP_200_OK
    assert second.json()["wishlisted"] is False
    assert not WishlistItem.objects.filter(user=user, product=product).exists()


def test_user_only_sees_their_own_wishlist(api_client, product):
    owner = UserFactory(email="owner@example.com", password="Str0ngPassw0rd!")
    other = UserFactory(email="other@example.com", password="Str0ngPassw0rd!")
    WishlistItem.objects.create(user=owner, product=product)

    login(api_client, other.email)
    response = api_client.get("/api/v1/wishlist/")
    assert response.json() == []


def test_wishlist_includes_nested_product_data(api_client, product):
    user = UserFactory(email="me2@example.com", password="Str0ngPassw0rd!")
    WishlistItem.objects.create(user=user, product=product)
    login(api_client, user.email)

    response = api_client.get("/api/v1/wishlist/")
    assert response.json()[0]["product"]["name"] == "Tournament Jersey"


def test_cannot_add_duplicate_via_create(api_client, product):
    user = UserFactory(email="dup@example.com", password="Str0ngPassw0rd!")
    login(api_client, user.email)

    api_client.post("/api/v1/wishlist/", {"product_id": product.id})
    response = api_client.post("/api/v1/wishlist/", {"product_id": product.id})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
