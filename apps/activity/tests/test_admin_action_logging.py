import pytest
from django.test import Client
from django.urls import reverse

from apps.activity.models import ActivityLog
from apps.orders.models import Order, OrderStatus
from apps.quotes.models import QuoteRequest, QuoteRequestStatus
from apps.users.admin_2fa import SESSION_VERIFIED_KEY
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client():
    admin = UserFactory(email="activityadmin@example.com", is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(admin)
    session = client.session
    session[SESSION_VERIFIED_KEY] = True
    session.save()
    return client, admin


def test_advance_status_row_logs_activity(admin_client, settings):
    client, admin = admin_client
    settings.ALLOWED_HOSTS = ["*"]
    order = Order.objects.create(
        reference_code="ORD-ACT0001",
        name="Activity Test",
        phone="+8801700000001",
        total_quantity=10,
        status=OrderStatus.CONFIRMED,
    )

    client.get(reverse("admin:orders_order_advance_status_row", args=[order.id]))

    entry = ActivityLog.objects.get()
    assert entry.actor == admin
    assert entry.verb == "advanced_status"
    assert entry.content_type.model == "order"
    assert entry.object_id == str(order.id)


def test_generate_chalan_row_logs_activity(admin_client, settings):
    client, admin = admin_client
    settings.ALLOWED_HOSTS = ["*"]
    order = Order.objects.create(
        reference_code="ORD-ACT0002",
        name="Activity Test 2",
        phone="+8801700000002",
        total_quantity=5,
        status=OrderStatus.CONFIRMED,
    )

    client.post(
        reverse("admin:orders_order_generate_chalan_row", args=[order.id]),
        {"_form_submitted": "true", "include_price": ""},
    )

    entry = ActivityLog.objects.get()
    assert entry.actor == admin
    assert entry.verb == "generated_chalan"
    assert "Generated chalan" in entry.description


def test_convert_to_order_row_logs_activity_against_the_quote(admin_client, settings):
    client, admin = admin_client
    settings.ALLOWED_HOSTS = ["*"]
    quote = QuoteRequest.objects.create(
        reference_code="QR-ACT0001",
        name="Activity Quote Test",
        phone="+8801700000003",
        quantity=10,
        status=QuoteRequestStatus.REVIEWED,
    )

    client.post(
        reverse("admin:quotes_quoterequest_convert_to_order_row", args=[quote.id]),
        {
            "_form_submitted": "true",
            "total_quantity": quote.quantity,
            "size_breakdown": "",
            "unit_price": "",
            "delivery_address": "",
        },
    )

    entry = ActivityLog.objects.get()
    assert entry.actor == admin
    assert entry.verb == "converted_to_order"
    assert entry.content_type.model == "quoterequest"
    assert entry.object_id == str(quote.id)
