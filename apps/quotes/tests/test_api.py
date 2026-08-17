import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import Category, Fabric
from apps.quotes.models import QuoteRequest, QuoteRequestStatus
from apps.users.tests.factories import UserFactory
from apps.users.tests.helpers import login as do_login

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def category():
    return Category.objects.create(slug="football", name="Football")


@pytest.fixture
def fabric():
    return Fabric.objects.create(name="Pin Mesh")


def test_guest_can_submit_quote_request(api_client, category, fabric):
    payload = {
        "name": "Rafiqul Islam",
        "phone": "+8801700000000",
        "email": "rafiq@example.com",
        "category": category.slug,
        "fabric": fabric.id,
        "quantity": 25,
        "size_breakdown": "5xS, 10xM, 10xL",
        "notes": "Need it in 3 weeks.",
    }
    response = api_client.post("/api/v1/quotes/", payload)
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["referenceCode"].startswith("QR-")
    assert body["estimatedPriceLow"] is not None

    quote = QuoteRequest.objects.get(reference_code=body["referenceCode"])
    assert quote.status == QuoteRequestStatus.PENDING
    # Guest submissions get an inactive shell account attached (not None) --
    # this is what all their history hangs off of until they claim it.
    assert quote.user is not None
    assert quote.user.email == "rafiq@example.com"
    assert quote.user.is_active is False
    assert not quote.user.has_usable_password()


def test_submission_requires_name_phone_quantity(api_client):
    response = api_client.post("/api/v1/quotes/", {})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    errors = response.json()["errors"]
    assert "name" in errors
    assert "phone" in errors
    assert "quantity" in errors


def test_logged_in_user_is_attached_to_their_quote(api_client, category):
    user = UserFactory(email="me@example.com", password="Str0ngPassw0rd!")
    do_login(api_client, "me@example.com")

    response = api_client.post("/api/v1/quotes/", {"name": "Me", "phone": "0170000", "quantity": 5})
    assert response.status_code == status.HTTP_201_CREATED
    quote = QuoteRequest.objects.get(reference_code=response.json()["referenceCode"])
    assert quote.user == user


def test_can_submit_with_a_design_file(api_client):
    file = SimpleUploadedFile("design.png", b"fake-image-bytes", content_type="image/png")
    response = api_client.post(
        "/api/v1/quotes/",
        {"name": "Sabbir", "phone": "0170000", "quantity": 12, "design_file": file},
        format="multipart",
    )
    assert response.status_code == status.HTTP_201_CREATED
    quote = QuoteRequest.objects.get(reference_code=response.json()["referenceCode"])
    assert quote.design_file.name


def test_rejects_disallowed_file_type(api_client):
    file = SimpleUploadedFile("virus.exe", b"x", content_type="application/octet-stream")
    response = api_client.post(
        "/api/v1/quotes/",
        {"name": "Bad File", "phone": "0170000", "quantity": 1, "design_file": file},
        format="multipart",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_anonymous_cannot_list_quote_requests(api_client):
    response = api_client.get("/api/v1/quotes/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_customer_cannot_set_status_on_create(api_client):
    response = api_client.post(
        "/api/v1/quotes/",
        {"name": "Sneaky", "phone": "0170000", "quantity": 1, "status": "converted"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    quote = QuoteRequest.objects.get(reference_code=response.json()["referenceCode"])
    assert quote.status == QuoteRequestStatus.PENDING


def test_staff_can_list_and_update_status(api_client, category):
    staff = UserFactory(email="staff@example.com", password="Str0ngPassw0rd!", is_staff=True)
    quote = QuoteRequest.objects.create(
        reference_code="QR-TEST0001", name="Customer", phone="0170000", quantity=10
    )

    do_login(api_client, "staff@example.com")

    list_response = api_client.get("/api/v1/quotes/")
    assert list_response.status_code == status.HTTP_200_OK

    patch_response = api_client.patch(
        f"/api/v1/quotes/{quote.id}/", {"status": "reviewed", "admin_notes": "Called customer."}
    )
    assert patch_response.status_code == status.HTTP_200_OK
    quote.refresh_from_db()
    assert quote.status == QuoteRequestStatus.REVIEWED
    assert quote.admin_notes == "Called customer."
    assert staff  # keep the fixture referenced explicitly for clarity


def test_staff_cannot_edit_customer_submitted_fields(api_client):
    UserFactory(email="staff2@example.com", password="Str0ngPassw0rd!", is_staff=True)
    quote = QuoteRequest.objects.create(
        reference_code="QR-TEST0002", name="Original Name", phone="0170000", quantity=10
    )

    do_login(api_client, "staff2@example.com")

    api_client.patch(f"/api/v1/quotes/{quote.id}/", {"name": "Tampered Name"})
    quote.refresh_from_db()
    assert quote.name == "Original Name"
