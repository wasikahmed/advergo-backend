from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.core import mail
from rest_framework import status
from rest_framework.test import APIClient

from apps.invoices.models import Invoice
from apps.orders.models import Order
from apps.users.tests.factories import UserFactory
from apps.users.tests.helpers import login

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def order_with_total():
    return Order.objects.create(
        reference_code="ORD-INVTEST1",
        name="Tanvir Hossain",
        phone="0170000",
        email="tanvir@example.com",
        total_quantity=10,
        unit_price=Decimal("500.00"),
        total_value=Decimal("5000.00"),
    )


@pytest.fixture
def order_without_total():
    return Order.objects.create(
        reference_code="ORD-INVTEST2", name="No Price Yet", phone="0170000", total_quantity=10
    )


def test_admin_can_generate_invoice(api_client, order_with_total):
    admin = UserFactory(email="admin@example.com", password="Str0ngPassw0rd!", is_staff=True)
    login(api_client, admin.email)
    mail.outbox.clear()  # drop the 2FA code email sent during login

    response = api_client.post(f"/api/v1/orders/{order_with_total.id}/generate_invoice/")
    assert response.status_code == status.HTTP_202_ACCEPTED

    # CELERY_TASK_ALWAYS_EAGER in test settings runs the task inline.
    invoice = Invoice.objects.get(order=order_with_total)
    assert invoice.pdf_file.name
    assert invoice.sent_at is not None
    assert len(mail.outbox) == 1
    assert admin  # keep fixture referenced


def test_generate_invoice_requires_total_value(api_client, order_without_total):
    admin = UserFactory(email="admin2@example.com", password="Str0ngPassw0rd!", is_staff=True)
    login(api_client, admin.email)

    response = api_client.post(f"/api/v1/orders/{order_without_total.id}/generate_invoice/")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not Invoice.objects.filter(order=order_without_total).exists()


def test_accounts_limited_cannot_generate_invoice(api_client, order_with_total):
    user = UserFactory(email="limited@example.com", password="Str0ngPassw0rd!")
    group, _ = Group.objects.get_or_create(name="AccountsLimited")
    user.groups.add(group)
    login(api_client, user.email)

    response = api_client.post(f"/api/v1/orders/{order_with_total.id}/generate_invoice/")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert not Invoice.objects.filter(order=order_with_total).exists()


def test_order_response_includes_invoice_once_generated(api_client, order_with_total):
    admin = UserFactory(email="admin3@example.com", password="Str0ngPassw0rd!", is_staff=True)
    login(api_client, admin.email)

    api_client.post(f"/api/v1/orders/{order_with_total.id}/generate_invoice/")
    response = api_client.get(f"/api/v1/orders/{order_with_total.id}/")
    assert response.json()["invoice"]["invoiceNumber"] == "INV-INVTEST1"


def test_order_response_invoice_is_null_before_generation(api_client, order_without_total):
    admin = UserFactory(email="admin4@example.com", password="Str0ngPassw0rd!", is_staff=True)
    login(api_client, admin.email)

    response = api_client.get(f"/api/v1/orders/{order_without_total.id}/")
    assert response.json()["invoice"] is None
