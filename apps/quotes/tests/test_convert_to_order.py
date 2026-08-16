import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.orders.models import Order
from apps.quotes.models import QuoteRequest, QuoteRequestStatus
from apps.users.tests.factories import UserFactory
from apps.users.tests.helpers import login as do_login

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def quote():
    return QuoteRequest.objects.create(
        reference_code="QR-CONVERT01",
        name="Rafiqul Islam",
        phone="0170000",
        quantity=25,
        size_breakdown="5xS, 20xM",
    )


def test_staff_can_convert_quote_to_order(api_client, quote):
    staff = UserFactory(email="staff@example.com", password="Str0ngPassw0rd!", is_staff=True)
    do_login(api_client, "staff@example.com")

    response = api_client.post(f"/api/v1/quotes/{quote.id}/convert_to_order/")
    assert response.status_code == status.HTTP_201_CREATED

    quote.refresh_from_db()
    assert quote.status == QuoteRequestStatus.CONVERTED

    order = Order.objects.get(quote_request=quote)
    assert order.name == "Rafiqul Islam"
    assert order.total_quantity == 25
    assert order.size_breakdown == "5xS, 20xM"
    assert order.created_by == staff
    assert staff  # keep fixture referenced


def test_non_staff_cannot_convert_quote(api_client, quote):
    customer = UserFactory(email="cust@example.com", password="Str0ngPassw0rd!")
    do_login(api_client, "cust@example.com")

    response = api_client.post(f"/api/v1/quotes/{quote.id}/convert_to_order/")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert not Order.objects.filter(quote_request=quote).exists()
    assert customer  # keep fixture referenced
