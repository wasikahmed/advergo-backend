from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.orders.models import Order
from apps.quotes.models import QuoteRequest, QuoteRequestStatus
from apps.users.admin_2fa import SESSION_VERIFIED_KEY
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client():
    admin = UserFactory(email="quotesadmin@example.com", is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(admin)
    session = client.session
    session[SESSION_VERIFIED_KEY] = True
    session.save()
    return client, admin


@pytest.fixture
def quote():
    return QuoteRequest.objects.create(
        reference_code="QR-DLGTEST1",
        name="Dialog Test Customer",
        phone="+8801788888888",
        quantity=20,
        size_breakdown="ORIGINAL: 5xS,15xM",
        status=QuoteRequestStatus.REVIEWED,
    )


def test_convert_dialog_prefills_from_quote(admin_client, quote, settings):
    client, _ = admin_client
    settings.ALLOWED_HOSTS = ["*"]

    url = reverse("admin:quotes_quoterequest_convert_to_order_row", args=[quote.id])
    response = client.get(url)
    content = response.content.decode()

    assert response.status_code == 200
    assert str(quote.quantity) in content
    assert quote.size_breakdown in content


def test_convert_dialog_lets_staff_override_values_without_touching_the_quote(
    admin_client, quote, settings
):
    client, admin = admin_client
    settings.ALLOWED_HOSTS = ["*"]

    url = reverse("admin:quotes_quoterequest_convert_to_order_row", args=[quote.id])
    response = client.post(
        url,
        {
            "_form_submitted": "true",
            "total_quantity": quote.quantity + 10,
            "size_breakdown": "ADJUSTED: 10xM, 10xL",
            "unit_price": "550.00",
            "delivery_address": "Adjusted Delivery Address, Dhaka",
        },
    )
    assert response.status_code == 302

    quote.refresh_from_db()
    assert quote.status == QuoteRequestStatus.CONVERTED
    assert quote.quantity == 20  # untouched
    assert quote.size_breakdown == "ORIGINAL: 5xS,15xM"  # untouched

    order = Order.objects.get(quote_request=quote)
    assert order.total_quantity == 30
    assert order.size_breakdown == "ADJUSTED: 10xM, 10xL"
    assert order.unit_price == Decimal("550.00")
    assert order.total_value == Decimal("16500.00")
    assert order.delivery_address == "Adjusted Delivery Address, Dhaka"
    assert order.created_by == admin


def test_convert_dialog_refuses_a_quote_that_already_has_an_order(admin_client, quote, settings):
    client, admin = admin_client
    settings.ALLOWED_HOSTS = ["*"]
    Order.objects.create(
        reference_code="ORD-EXISTING1",
        quote_request=quote,
        name=quote.name,
        phone=quote.phone,
        total_quantity=quote.quantity,
        created_by=admin,
    )

    url = reverse("admin:quotes_quoterequest_convert_to_order_row", args=[quote.id])
    response = client.post(
        url,
        {
            "_form_submitted": "true",
            "total_quantity": quote.quantity,
            "size_breakdown": "",
            "unit_price": "",
            "delivery_address": "",
        },
    )

    # No has_*_permission gate on this action -- the in-body guard handles
    # it: redirects with a warning, no duplicate order.
    assert response.status_code == 302
    assert Order.objects.filter(quote_request=quote).count() == 1


def test_convert_dialog_allows_a_quote_whose_status_was_edited_by_hand(
    admin_client, quote, settings
):
    """
    status is a plain editable field (including list_editable on the
    changelist), so it can say "Converted to order" from a manual edit that
    never actually created one. The guard has to check for a real Order
    row, not the status label, or a quote like this could never be
    genuinely converted.
    """
    client, _ = admin_client
    settings.ALLOWED_HOSTS = ["*"]
    quote.status = QuoteRequestStatus.CONVERTED
    quote.save(update_fields=["status"])

    url = reverse("admin:quotes_quoterequest_convert_to_order_row", args=[quote.id])
    response = client.post(
        url,
        {
            "_form_submitted": "true",
            "total_quantity": quote.quantity,
            "size_breakdown": "",
            "unit_price": "",
            "delivery_address": "",
        },
    )

    assert response.status_code == 302
    assert Order.objects.filter(quote_request=quote).exists()
