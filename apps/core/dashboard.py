import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

DEFAULT_RANGE_LENGTH = timedelta(days=29)  # 30 days inclusive of both ends
MAX_RANGE_LENGTH = timedelta(days=366)

#: Every section's date-range controls are independent -- each key prefixes
#: its own `{key}_from`/`{key}_to` query params so picking a range for one
#: section doesn't disturb the others sharing the same URL.
SECTION_KEYS = ("orders", "quotes", "engagement", "admin")


def _parse_date(value, default):
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default


def _section_range(request, key):
    today = timezone.localdate()
    start = _parse_date(request.GET.get(f"{key}_from"), today - DEFAULT_RANGE_LENGTH)
    end = _parse_date(request.GET.get(f"{key}_to"), today)
    if start > end:
        start, end = end, start
    if end - start > MAX_RANGE_LENGTH:
        start = end - MAX_RANGE_LENGTH
    return start, end


def _day_bounds(day: date, end_of_day: bool):
    return timezone.make_aware(datetime.combine(day, time.max if end_of_day else time.min))


def _daily_trend(queryset, start: date, end: date, *, date_field="created_at"):
    """
    "count per day across [start, end]", zero-filled -- ready to drop
    straight into an Unfold chart/line.html `data` context var. Zero-filling
    matters here: without it, a quiet day just disappears from the x-axis
    instead of showing as a dip, which reads as missing data rather than "no
    activity that day".
    """
    counts_by_date = {
        row["day"]: row["count"]
        for row in (
            queryset.filter(
                **{
                    f"{date_field}__gte": _day_bounds(start, end_of_day=False),
                    f"{date_field}__lte": _day_bounds(end, end_of_day=True),
                }
            )
            .annotate(day=TruncDate(date_field))
            .values("day")
            .annotate(count=Count("id"))
        )
    }

    labels, counts = [], []
    day = start
    while day <= end:
        labels.append(day.strftime("%b %d"))
        counts.append(counts_by_date.get(day, 0))
        day += timedelta(days=1)
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


def _in_range(queryset, start, end, *, date_field="created_at"):
    return queryset.filter(
        **{
            f"{date_field}__gte": _day_bounds(start, end_of_day=False),
            f"{date_field}__lte": _day_bounds(end, end_of_day=True),
        }
    )


def _orders_section(request, start, end):
    if not request.user.has_perm("orders.view_order"):
        return None

    from apps.orders.models import Order, OrderStatus

    orders = Order.objects.all()
    active = orders.exclude(status=OrderStatus.CANCELLED)

    status_counts = dict(orders.values_list("status").annotate(count=Count("id")))
    labels, counts = _daily_trend(orders, start, end)
    status_breakdown = [
        {"label": label, "value": status_counts.get(value, 0)} for value, label in OrderStatus.choices
    ]

    return {
        "title": "Orders & fulfillment",
        "range_key": "orders",
        "range_start": start,
        "range_end": end,
        "kpis": [
            {"title": "Total orders", "value": orders.count()},
            {
                "title": "Order value (confirmed)",
                "value": _money(active.aggregate(total=Sum("total_value"))["total"]),
            },
            {"title": "New in range", "value": _in_range(orders, start, end).count()},
        ],
        "status_breakdown": status_breakdown,
        "status_breakdown_table": _breakdown_table(status_breakdown),
        "trend_chart": _line_chart_data("Orders", labels, counts),
    }


def _quotes_section(request, start, end):
    if not request.user.has_perm("quotes.view_quoterequest"):
        return None

    from apps.quotes.models import QuoteRequest, QuoteRequestStatus

    quotes = QuoteRequest.objects.all()
    total = quotes.count()
    converted = quotes.filter(status=QuoteRequestStatus.CONVERTED).count()
    conversion_rate = round((converted / total) * 100, 1) if total else 0

    status_counts = dict(quotes.values_list("status").annotate(count=Count("id")))
    labels, counts = _daily_trend(quotes, start, end)
    status_breakdown = [
        {"label": label, "value": status_counts.get(value, 0)} for value, label in QuoteRequestStatus.choices
    ]

    return {
        "title": "Quotes & conversion",
        "range_key": "quotes",
        "range_start": start,
        "range_end": end,
        "kpis": [
            {"title": "Total quote requests", "value": total},
            {"title": "Conversion rate", "value": f"{conversion_rate}%"},
            {"title": "Pending review", "value": status_counts.get(QuoteRequestStatus.PENDING, 0)},
        ],
        "status_breakdown": status_breakdown,
        "status_breakdown_table": _breakdown_table(status_breakdown),
        "trend_chart": _line_chart_data("Quote requests", labels, counts),
    }


def _engagement_section(request, start, end):
    from apps.users.models import User

    if not request.user.has_perm("users.view_user"):
        return None

    customers = User.objects.filter(is_staff=False)
    labels, counts = _daily_trend(customers, start, end)

    kpis = [
        {"title": "New customers in range", "value": _in_range(customers, start, end).count()},
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
        "range_key": "engagement",
        "range_start": start,
        "range_end": end,
        "kpis": kpis,
        "trend_chart": _line_chart_data("New customers", labels, counts),
    }


def _admin_section(request, start, end):
    if not request.user.has_perm("activity.view_loginevent"):
        return None

    from apps.activity.models import LoginEvent

    in_range = _in_range(LoginEvent.objects.all(), start, end)
    total = in_range.count()
    failed = in_range.filter(success=False).count()
    failure_rate = round((failed / total) * 100, 1) if total else 0

    channel_counts = dict(in_range.values_list("channel").annotate(count=Count("id")))
    channel_breakdown = [
        {"label": label, "value": channel_counts.get(value, 0)}
        for value, label in LoginEvent._meta.get_field("channel").choices
    ]

    return {
        "title": "Admin & security",
        "range_key": "admin",
        "range_start": start,
        "range_end": end,
        "kpis": [
            {"title": "Logins in range", "value": total},
            {"title": "Failed logins in range", "value": failed},
            {"title": "Failure rate", "value": f"{failure_rate}%"},
        ],
        "channel_breakdown": channel_breakdown,
        "channel_breakdown_table": {
            "headers": ["Channel", "Count"],
            "rows": [[row["label"], row["value"]] for row in channel_breakdown],
        },
    }


def dashboard_callback(request, context):
    ranges = {key: _section_range(request, key) for key in SECTION_KEYS}

    sections = [
        section
        for section in (
            _orders_section(request, *ranges["orders"]),
            _quotes_section(request, *ranges["quotes"]),
            _engagement_section(request, *ranges["engagement"]),
            _admin_section(request, *ranges["admin"]),
        )
        if section is not None
    ]
    context["dashboard_sections"] = sections
    context["dashboard_all_ranges"] = [
        {"key": key, "start": start, "end": end} for key, (start, end) in ranges.items()
    ]
    return context
