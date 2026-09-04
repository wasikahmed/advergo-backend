import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import Category, Product
from apps.reviews.models import ProductReview, ReviewStatus
from apps.users.tests.factories import UserFactory
from apps.users.tests.helpers import login

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def product():
    category = Category.objects.create(slug="football", name="Football")
    return Product.objects.create(name="Tournament Jersey", category=category)


def test_anonymous_cannot_submit_a_review(api_client, product):
    response = api_client.post(
        "/api/v1/reviews/product/", {"product": product.id, "rating": 5, "text": "Great fit"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_authenticated_submission_starts_pending_and_is_not_publicly_listed(api_client, product):
    user = UserFactory(email="reviewer@example.com", password="Str0ngPassw0rd!")
    login(api_client, user.email)

    response = api_client.post(
        "/api/v1/reviews/product/", {"product": product.id, "rating": 4, "text": "Good quality"}
    )
    assert response.status_code == status.HTTP_201_CREATED

    review = ProductReview.objects.get(product=product, user=user)
    assert review.status == ReviewStatus.PENDING

    listing = api_client.get(f"/api/v1/reviews/product/?product={product.id}")
    assert listing.json() == []


def test_list_only_returns_approved_reviews_for_that_product(api_client, product):
    other_category = Category.objects.create(slug="cricket", name="Cricket")
    other_product = Product.objects.create(name="Cricket Kit", category=other_category)
    reviewer = UserFactory(email="a@example.com", password="Str0ngPassw0rd!")
    other_reviewer = UserFactory(email="b@example.com", password="Str0ngPassw0rd!")

    ProductReview.objects.create(
        product=product, user=reviewer, rating=5, text="Approved", status=ReviewStatus.APPROVED
    )
    ProductReview.objects.create(
        product=product,
        user=other_reviewer,
        rating=3,
        text="Still pending",
        status=ReviewStatus.PENDING,
    )
    ProductReview.objects.create(
        product=other_product,
        user=reviewer,
        rating=5,
        text="Wrong product",
        status=ReviewStatus.APPROVED,
    )

    response = api_client.get(f"/api/v1/reviews/product/?product={product.id}")
    texts = {r["text"] for r in response.json()}
    assert texts == {"Approved"}


def test_cannot_review_the_same_product_twice(api_client, product):
    user = UserFactory(email="dup@example.com", password="Str0ngPassw0rd!")
    login(api_client, user.email)

    first = api_client.post(
        "/api/v1/reviews/product/", {"product": product.id, "rating": 5, "text": "First"}
    )
    assert first.status_code == status.HTTP_201_CREATED

    second = api_client.post(
        "/api/v1/reviews/product/", {"product": product.id, "rating": 2, "text": "Second"}
    )
    assert second.status_code == status.HTTP_400_BAD_REQUEST
