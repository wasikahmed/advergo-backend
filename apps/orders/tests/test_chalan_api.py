from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

from apps.invoices.models import Chalan
from apps.orders.models import Order
from apps.users.tests.factories import UserFactory
from apps.users.tests.helpers import login

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def order():
    return Order.objects.create(
        reference_code="ORD-CHLNTST1",
        name="Sabbir Rahman",
        phone="0170000",
        delivery_address="House 12, Road 5, Dhaka",
        total_quantity=10,
        unit_price=Decimal("500.00"),
        total_value=Decimal("5000.00"),
    )


def test_admin_can_generate_chalan_without_price(api_client, order):
    admin = UserFactory(email="chlnadmin@example.com", password="Str0ngPassw0rd!", is_staff=True)
    login(api_client, admin.email)

    response = api_client.post(f"/api/v1/orders/{order.id}/generate_chalan/")
    assert response.status_code == status.HTTP_202_ACCEPTED

    chalan = Chalan.objects.get(order=order)
    assert chalan.include_price is False
    assert chalan.pdf_file.name
    assert chalan.chalan_number == "CHLN-CHLNTST1"


def test_admin_can_generate_chalan_with_price(api_client, order):
    admin = UserFactory(email="chlnadmin2@example.com", password="Str0ngPassw0rd!", is_staff=True)
    login(api_client, admin.email)

    response = api_client.post(
        f"/api/v1/orders/{order.id}/generate_chalan/", {"includePrice": True}
    )
    assert response.status_code == status.HTTP_202_ACCEPTED

    chalan = Chalan.objects.get(order=order)
    assert chalan.include_price is True


def test_regenerating_chalan_keeps_history(api_client, order):
    admin = UserFactory(email="chlnadmin3@example.com", password="Str0ngPassw0rd!", is_staff=True)
    login(api_client, admin.email)

    api_client.post(f"/api/v1/orders/{order.id}/generate_chalan/")
    api_client.post(f"/api/v1/orders/{order.id}/generate_chalan/")

    assert Chalan.objects.filter(order=order).count() == 2


def test_accounts_limited_cannot_generate_chalan(api_client, order):
    user = UserFactory(email="chlnlimited@example.com", password="Str0ngPassw0rd!")
    group, _ = Group.objects.get_or_create(name="AccountsLimited")
    user.groups.add(group)
    login(api_client, user.email)

    response = api_client.post(f"/api/v1/orders/{order.id}/generate_chalan/")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert not Chalan.objects.filter(order=order).exists()
