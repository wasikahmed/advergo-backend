import json
from datetime import date, timedelta

import pytest
from django.contrib.auth.models import Permission
from django.test import RequestFactory
from django.utils import timezone

from apps.core.dashboard import dashboard_callback
from apps.orders.models import Order, OrderStatus
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _request_for(user, params=None):
    request = RequestFactory().get("/admin/", params or {})
    request.user = user
    return request


def test_dashboard_hides_section_without_permission():
    user = UserFactory(email="noperm@example.com", is_staff=True)
    context = dashboard_callback(_request_for(user), {})
    assert context["dashboard_sections"] == []


def test_dashboard_shows_orders_section_with_permission():
    user = UserFactory(email="orderviewer@example.com", is_staff=True)
    user.user_permissions.add(
        Permission.objects.get(codename="view_order", content_type__app_label="orders")
    )

    context = dashboard_callback(_request_for(user), {})

    titles = [section["title"] for section in context["dashboard_sections"]]
    assert "Orders & fulfillment" in titles
    assert "Quotes & conversion" not in titles


def test_orders_section_excludes_cancelled_from_value():
    user = UserFactory(email="orderviewer2@example.com", is_staff=True)
    user.user_permissions.add(
        Permission.objects.get(codename="view_order", content_type__app_label="orders")
    )
    customer = UserFactory(email="cust@example.com")

    Order.objects.create(
        reference_code="ORD-DASH1",
        customer=customer,
        name="A",
        phone="1",
        total_quantity=1,
        total_value=1000,
        status=OrderStatus.CONFIRMED,
    )
    Order.objects.create(
        reference_code="ORD-DASH2",
        customer=customer,
        name="B",
        phone="2",
        total_quantity=1,
        total_value=5000,
        status=OrderStatus.CANCELLED,
    )

    context = dashboard_callback(_request_for(user), {})
    orders_section = next(
        s for s in context["dashboard_sections"] if s["title"] == "Orders & fulfillment"
    )
    value_kpi = next(k for k in orders_section["kpis"] if k["title"] == "Order value (confirmed)")
    assert "1,000" in value_kpi["value"]
    assert "5,000" not in value_kpi["value"]


def test_engagement_section_omits_optional_kpis_without_permission():
    user = UserFactory(email="usersonly@example.com", is_staff=True)
    user.user_permissions.add(
        Permission.objects.get(codename="view_user", content_type__app_label="users")
    )

    context = dashboard_callback(_request_for(user), {})
    engagement = next(
        s for s in context["dashboard_sections"] if s["title"] == "Customer engagement"
    )
    kpi_titles = [k["title"] for k in engagement["kpis"]]
    assert "Wishlist items" not in kpi_titles
    assert "Avg. review rating" not in kpi_titles


def test_default_range_is_last_30_days():
    user = UserFactory(email="ranged@example.com", is_staff=True)
    context = dashboard_callback(_request_for(user), {})
    orders_range = next(r for r in context["dashboard_all_ranges"] if r["key"] == "orders")
    today = timezone.localdate()
    assert orders_range["end"] == today
    assert orders_range["start"] == today - timedelta(days=29)


def test_section_range_selectable_independently():
    user = UserFactory(email="ranged2@example.com", is_staff=True)
    user.user_permissions.add(
        Permission.objects.get(codename="view_order", content_type__app_label="orders")
    )
    user.user_permissions.add(
        Permission.objects.get(codename="view_quoterequest", content_type__app_label="quotes")
    )

    context = dashboard_callback(
        _request_for(user, {"orders_from": "2026-01-01", "orders_to": "2026-01-07"}), {}
    )

    orders_section = next(
        s for s in context["dashboard_sections"] if s["title"] == "Orders & fulfillment"
    )
    assert orders_section["range_start"] == date(2026, 1, 1)
    assert orders_section["range_end"] == date(2026, 1, 7)

    quotes_section = next(
        s for s in context["dashboard_sections"] if s["title"] == "Quotes & conversion"
    )
    today = timezone.localdate()
    # Quotes' own range wasn't touched by the orders_* params -- confirms
    # each section's range is independent, not a shared global toggle.
    assert quotes_section["range_end"] == today
    assert quotes_section["range_start"] == today - timedelta(days=29)


def test_invalid_range_falls_back_to_default():
    user = UserFactory(email="ranged3@example.com", is_staff=True)
    user.user_permissions.add(
        Permission.objects.get(codename="view_order", content_type__app_label="orders")
    )

    context = dashboard_callback(_request_for(user, {"orders_from": "not-a-date"}), {})

    orders_section = next(
        s for s in context["dashboard_sections"] if s["title"] == "Orders & fulfillment"
    )
    today = timezone.localdate()
    assert orders_section["range_start"] == today - timedelta(days=29)


def test_range_affects_trend_and_kpi_window():
    user = UserFactory(email="ranged4@example.com", is_staff=True)
    user.user_permissions.add(
        Permission.objects.get(codename="view_order", content_type__app_label="orders")
    )

    context = dashboard_callback(
        _request_for(user, {"orders_from": "2026-01-01", "orders_to": "2026-01-07"}), {}
    )
    orders_section = next(
        s for s in context["dashboard_sections"] if s["title"] == "Orders & fulfillment"
    )
    kpi_titles = [k["title"] for k in orders_section["kpis"]]
    assert "New in range" in kpi_titles

    trend_labels = json.loads(orders_section["trend_chart"])["labels"]
    assert len(trend_labels) == 7


def test_admin_section_has_no_recent_activity_table():
    user = UserFactory(email="admintest@example.com", is_staff=True)
    user.user_permissions.add(
        Permission.objects.get(codename="view_loginevent", content_type__app_label="activity")
    )
    user.user_permissions.add(
        Permission.objects.get(codename="view_activitylog", content_type__app_label="activity")
    )

    context = dashboard_callback(_request_for(user), {})
    admin_section = next(
        s for s in context["dashboard_sections"] if s["title"] == "Admin & security"
    )
    assert "recent_activity" not in admin_section
