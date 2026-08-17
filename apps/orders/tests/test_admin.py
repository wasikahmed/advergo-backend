from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.invoices.models import Invoice
from apps.orders.models import Order, OrderStatus
from apps.users.admin_2fa import SESSION_VERIFIED_KEY
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client():
    admin = UserFactory(email="ordersadmin@example.com", is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(admin)
    session = client.session
    session[SESSION_VERIFIED_KEY] = True
    session.save()
    return client, admin


@pytest.fixture
def order():
    return Order.objects.create(
        reference_code="ORD-ADMTEST1",
        name="Pipeline Test",
        phone="+8801700000000",
        total_quantity=10,
        status=OrderStatus.CONFIRMED,
    )


def test_advance_status_row_moves_one_step(admin_client, order, settings):
    client, _ = admin_client
    settings.ALLOWED_HOSTS = ["*"]

    url = reverse("admin:orders_order_advance_status_row", args=[order.id])
    response = client.get(url)

    assert response.status_code == 302
    order.refresh_from_db()
    assert order.status == OrderStatus.IN_PRODUCTION


def test_advance_status_row_stops_at_delivered(admin_client, order, settings):
    client, _ = admin_client
    settings.ALLOWED_HOSTS = ["*"]
    order.status = OrderStatus.DELIVERED
    order.save(update_fields=["status"])

    url = reverse("admin:orders_order_advance_status_row", args=[order.id])
    client.get(url)

    order.refresh_from_db()
    assert order.status == OrderStatus.DELIVERED  # unchanged


def test_cancel_order_row(admin_client, order, settings):
    client, _ = admin_client
    settings.ALLOWED_HOSTS = ["*"]

    url = reverse("admin:orders_order_cancel_order_row", args=[order.id])
    response = client.get(url)

    assert response.status_code == 302
    order.refresh_from_db()
    assert order.status == OrderStatus.CANCELLED


def test_generate_invoice_row_requires_total_value(admin_client, order, settings):
    client, _ = admin_client
    settings.ALLOWED_HOSTS = ["*"]
    assert order.total_value is None

    url = reverse("admin:orders_order_generate_invoice_row", args=[order.id])
    client.get(url)

    assert not Invoice.objects.filter(order=order).exists()


def test_generate_invoice_row_creates_invoice(admin_client, order, settings):
    client, admin = admin_client
    settings.ALLOWED_HOSTS = ["*"]
    order.total_value = Decimal("5000.00")
    order.unit_price = Decimal("500.00")
    order.save(update_fields=["total_value", "unit_price"])

    url = reverse("admin:orders_order_generate_invoice_row", args=[order.id])
    response = client.get(url)

    assert response.status_code == 302
    invoice = Invoice.objects.get(order=order)
    assert invoice.generated_by == admin
