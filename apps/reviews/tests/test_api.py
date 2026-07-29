import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.reviews.models import Review, ReviewStatus

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_list_only_returns_approved_reviews(api_client):
    Review.objects.create(name="Approved", rating=5, text="Great", status=ReviewStatus.APPROVED)
    Review.objects.create(name="Pending", rating=5, text="Great", status=ReviewStatus.PENDING)
    Review.objects.create(name="Rejected", rating=1, text="Bad", status=ReviewStatus.REJECTED)

    response = api_client.get("/api/v1/reviews/")
    names = {r["name"] for r in response.data}
    assert names == {"Approved"}


def test_public_submission_starts_pending_and_is_not_publicly_listed(api_client):
    response = api_client.post(
        "/api/v1/reviews/",
        {"name": "New Customer", "organization": "Acme", "rating": 5, "text": "Loved it"},
    )
    assert response.status_code == status.HTTP_201_CREATED

    review = Review.objects.get(name="New Customer")
    assert review.status == ReviewStatus.PENDING

    listing = api_client.get("/api/v1/reviews/")
    assert "New Customer" not in {r["name"] for r in listing.data}


def test_submission_cannot_set_status_directly(api_client):
    response = api_client.post(
        "/api/v1/reviews/",
        {"name": "Sneaky", "rating": 5, "text": "x", "status": "approved"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Review.objects.get(name="Sneaky").status == ReviewStatus.PENDING


def test_rating_out_of_range_is_rejected(api_client):
    response = api_client.post("/api/v1/reviews/", {"name": "Bad Rating", "rating": 7, "text": "x"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
