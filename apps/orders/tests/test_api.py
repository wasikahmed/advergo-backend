from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

from apps.orders.models import Order, OrderStatus
from apps.users.tests.factories import UserFactory
from apps.users.tests.helpers import login

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer():
    return UserFactory(email="customer@example.com", password="Str0ngPassw0rd!")


@pytest.fixture
def other_customer():
    return UserFactory(email="other@example.com", password="Str0ngPassw0rd!")


@pytest.fixture
def admin_user():
    return UserFactory(email="admin@example.com", password="Str0ngPassw0rd!", is_staff=True)


@pytest.fixture
def accounts_full_user():
    user = UserFactory(email="accountsfull@example.com", password="Str0ngPassw0rd!")
    group, _ = Group.objects.get_or_create(name="AccountsFull")
    user.groups.add(group)
    return user


@pytest.fixture
def accounts_limited_user():
    user = UserFactory(email="accountslimited@example.com", password="Str0ngPassw0rd!")
    group, _ = Group.objects.get_or_create(name="AccountsLimited")
    user.groups.add(group)
    return user


def make_order(**kwargs):
    defaults = {
        "reference_code": f"ORD-{Order.objects.count() + 1:06d}",
        "name": "Customer",
        "phone": "0170000",
        "total_quantity": 20,
        "unit_price": Decimal("500.00"),
        "total_value": Decimal("10000.00"),
        "advance_paid": Decimal("2000.00"),
    }
    defaults.update(kwargs)
    return Order.objects.create(**defaults)


def test_anonymous_cannot_access_orders(api_client):
    response = api_client.get("/api/v1/orders/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_customer_only_sees_their_own_orders(api_client, customer, other_customer):
    make_order(customer=customer, reference_code="ORD-MINE")
    make_order(customer=other_customer, reference_code="ORD-NOT-MINE")

    login(api_client, customer.email)
    response = api_client.get("/api/v1/orders/")
    codes = {o["referenceCode"] for o in response.json()["results"]}
    assert codes == {"ORD-MINE"}


def test_customer_sees_full_financials_of_own_order(api_client, customer):
    make_order(customer=customer, reference_code="ORD-MINE", total_value=Decimal("10000.00"))

    login(api_client, customer.email)
    response = api_client.get("/api/v1/orders/")
    order = response.json()["results"][0]
    assert order["totalValue"] == "10000.00"
    assert order["dueAmount"] == "8000.00"


def test_customer_cannot_create_order(api_client, customer):
    login(api_client, customer.email)
    response = api_client.post("/api/v1/orders/", {"name": "x", "phone": "x", "total_quantity": 1})
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_can_create_order_with_auto_reference_code(api_client, admin_user):
    login(api_client, admin_user.email)
    response = api_client.post(
        "/api/v1/orders/", {"name": "Walk-in", "phone": "0170000", "totalQuantity": 30}
    )
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["referenceCode"].startswith("ORD-")


def test_accounts_full_sees_all_orders_with_financials(api_client, accounts_full_user, customer):
    make_order(customer=customer, reference_code="ORD-A", unit_price=Decimal("100.00"))

    login(api_client, accounts_full_user.email)
    response = api_client.get("/api/v1/orders/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["results"][0]["unitPrice"] == "100.00"


def test_accounts_full_can_update_order_status(api_client, accounts_full_user, customer):
    order = make_order(customer=customer, reference_code="ORD-A")

    login(api_client, accounts_full_user.email)
    response = api_client.patch(f"/api/v1/orders/{order.id}/", {"status": "in_production"})
    assert response.status_code == status.HTTP_200_OK
    order.refresh_from_db()
    assert order.status == OrderStatus.IN_PRODUCTION


def test_accounts_limited_sees_all_orders_without_financials(
    api_client, accounts_limited_user, customer
):
    make_order(customer=customer, reference_code="ORD-A", unit_price=Decimal("999.00"))

    login(api_client, accounts_limited_user.email)
    response = api_client.get("/api/v1/orders/")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()["results"][0]
    assert body["referenceCode"] == "ORD-A"
    assert "unitPrice" not in body
    assert "totalValue" not in body
    assert "advancePaid" not in body
    assert "dueAmount" not in body


def test_accounts_limited_cannot_write(api_client, accounts_limited_user, customer):
    order = make_order(customer=customer, reference_code="ORD-A")

    login(api_client, accounts_limited_user.email)
    response = api_client.patch(f"/api/v1/orders/{order.id}/", {"status": "delivered"})
    assert response.status_code == status.HTTP_403_FORBIDDEN
