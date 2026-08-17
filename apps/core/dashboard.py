import json
from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.formats import date_format

from apps.core.admin_utils import user_chip

DEFAULT_RANGE_DAYS = 30
AVAILABLE_RANGE_DAYS = (7, 30, 90)


def _selected_range_days(request) -> int:
    try:
        days = int(request.GET.get("days", DEFAULT_RANGE_DAYS))
    except (TypeError, ValueError):
        return DEFAULT_RANGE_DAYS
    return days if days in AVAILABLE_RANGE_DAYS else DEFAULT_RANGE_DAYS


def _daily_trend(queryset, days, *, date_field="created_at"):
    """
    "count per day for the selected range", zero-filled -- ready to drop
    straight into an Unfold chart/line.html `data` context var. Zero-filling
    matters here: without it, a quiet day just disappears from the x-axis
    instead of showing as a dip, which reads as missing data rather than "no
    activity that day".
    """
    since = timezone.now() - timedelta(days=days - 1)
    counts_by_date = {
        row["day"]: row["count"]
        for row in (
            queryset.filter(**{f"{date_field}__gte": since})
            .annotate(day=TruncDate(date_field))
            .values("day")
            .annotate(count=Count("id"))
        )
    }

    today = timezone.localdate()
    labels, counts = [], []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        labels.append(day.strftime("%b %d"))
        counts.append(counts_by_date.get(day, 0))
    return labels, counts


def _line_chart_data(label, labels, values):
    return json.dumps(
        {
            "labels": labels,
            "datasets": [{"label": label, "data": values, "borderColor": "#c8262c"}],
        }
    )


def _money(value) -> str:
    return f"৳{value or Decimal(0):,.0f}"


def _breakdown_table(rows):
    return {"headers": ["Status", "Count"], "rows": [[row["label"], row["value"]] for row in rows]}


def _orders_section(request, days):
    if not request.user.has_perm("orders.view_order"):
        return None

    from apps.orders.models import Order, OrderStatus

    orders = Order.objects.all()
    active = orders.exclude(status=OrderStatus.CANCELLED)
    since = timezone.now() - timedelta(days=days)

    status_counts = dict(orders.values_list("status").annotate(count=Count("id")))
    labels, counts = _daily_trend(orders, days)
    status_breakdown = [
        {"label": label, "value": status_counts.get(value, 0)} for value, label in OrderStatus.choices
    ]

    return {
        "title": "Orders & fulfillment",
        "kpis": [
            {"title": "Total orders", "value": orders.count()},
            {
                "title": "Order value (confirmed)",
                "value": _money(active.aggregate(total=Sum("total_value"))["total"]),
            },
            {"title": f"New in last {days} days", "value": orders.filter(created_at__gte=since).count()},
        ],
        "status_breakdown": status_breakdown,
        "status_breakdown_table": _breakdown_table(status_breakdown),
        "trend_chart": _line_chart_data("Orders", labels, counts),
    }


def _quotes_section(request, days):
    if not request.user.has_perm("quotes.view_quoterequest"):
        return None

    from apps.quotes.models import QuoteRequest, QuoteRequestStatus

    quotes = QuoteRequest.objects.all()
    total = quotes.count()
    converted = quotes.filter(status=QuoteRequestStatus.CONVERTED).count()
    conversion_rate = round((converted / total) * 100, 1) if total else 0

    status_counts = dict(quotes.values_list("status").annotate(count=Count("id")))
    labels, counts = _daily_trend(quotes, days)
    status_breakdown = [
        {"label": label, "value": status_counts.get(value, 0)} for value, label in QuoteRequestStatus.choices
    ]

    return {
        "title": "Quotes & conversion",
        "kpis": [
            {"title": "Total quote requests", "value": total},
            {"title": "Conversion rate", "value": f"{conversion_rate}%"},
            {"title": "Pending review", "value": status_counts.get(QuoteRequestStatus.PENDING, 0)},
        ],
        "status_breakdown": status_breakdown,
        "status_breakdown_table": _breakdown_table(status_breakdown),
        "trend_chart": _line_chart_data("Quote requests", labels, counts),
    }


def _engagement_section(request, days):
    from apps.users.models import User

    if not request.user.has_perm("users.view_user"):
        return None

    since = timezone.now() - timedelta(days=days)
    customers = User.objects.filter(is_staff=False)
    labels, counts = _daily_trend(customers, days)

    kpis = [
        {"title": f"New customers ({days}d)", "value": customers.filter(created_at__gte=since).count()},
        {"title": "Total customers", "value": customers.count()},
    ]

    if request.user.has_perm("wishlist.view_wishlistitem"):
        from apps.wishlist.models import WishlistItem

        kpis.append({"title": "Wishlist items", "value": WishlistItem.objects.count()})

    if request.user.has_perm("reviews.view_review"):
        from apps.reviews.models import Review

        avg_rating = Review.objects.aggregate(avg=Avg("rating"))["avg"]
        kpis.append(
            {
                "title": "Avg. review rating",
                "value": f"{avg_rating:.1f}★" if avg_rating else "—",
            }
        )

    return {
        "title": "Customer engagement",
        "kpis": kpis,
        "trend_chart": _line_chart_data("New customers", labels, counts),
    }


def _admin_section(request, days):
    if not request.user.has_perm("activity.view_loginevent"):
        return None

    from apps.activity.models import LoginEvent

    since = timezone.now() - timedelta(days=days)
    recent = LoginEvent.objects.filter(created_at__gte=since)
    total = recent.count()
    failed = recent.filter(success=False).count()
    failure_rate = round((failed / total) * 100, 1) if total else 0

    channel_counts = dict(recent.values_list("channel").annotate(count=Count("id")))
    channel_breakdown = [
        {"label": label, "value": channel_counts.get(value, 0)}
        for value, label in LoginEvent._meta.get_field("channel").choices
    ]

    section = {
        "title": "Admin & security",
        "kpis": [
            {"title": f"Logins ({days}d)", "value": total},
            {"title": f"Failed logins ({days}d)", "value": failed},
            {"title": "Failure rate", "value": f"{failure_rate}%"},
        ],
        "channel_breakdown": channel_breakdown,
        "channel_breakdown_table": {
            "headers": ["Channel", "Count"],
            "rows": [[row["label"], row["value"]] for row in channel_breakdown],
        },
    }

    if request.user.has_perm("activity.view_activitylog"):
        from apps.activity.models import ActivityLog

        entries = ActivityLog.objects.select_related("actor").order_by("-created_at")[:8]
        section["recent_activity"] = {
            "headers": ["When", "Who", "Did", "What"],
            "rows": [
                [
                    date_format(entry.created_at, "SHORT_DATETIME_FORMAT"),
                    user_chip(entry.actor),
                    entry.verb,
                    entry.object_repr or "—",
                ]
                for entry in entries
            ],
        }

    return section


def dashboard_callback(request, context):
    days = _selected_range_days(request)
    sections = [
        section
        for section in (
            _orders_section(request, days),
            _quotes_section(request, days),
            _engagement_section(request, days),
            _admin_section(request, days),
        )
        if section is not None
    ]
    context["dashboard_sections"] = sections
    context["dashboard_range_days"] = days
    context["dashboard_range_label"] = f"Last {days} days"
    context["dashboard_range_options"] = AVAILABLE_RANGE_DAYS
    return context
