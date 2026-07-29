from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.catalog.models import Fabric, Product, SportCategory
from apps.core.models import TimeStampedModel
from apps.quotes.models import QuoteRequest


class OrderStatus(models.TextChoices):
    CONFIRMED = "confirmed", "Confirmed"
    IN_PRODUCTION = "in_production", "In production"
    QUALITY_CHECK = "quality_check", "Quality check"
    READY = "ready", "Ready for delivery"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"


class Order(TimeStampedModel):
    """
    A confirmed order -- created by staff after a QuoteRequest is reviewed and
    the customer is contacted directly (spec: no online payment; staff enters
    quantities/price/advance once terms are agreed by phone).
    """

    reference_code = models.CharField(max_length=20, unique=True, editable=False)
    quote_request = models.ForeignKey(
        QuoteRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
        help_text="Linked account, if the customer has one -- lets them see this order + invoice.",
    )

    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

    category = models.ForeignKey(
        SportCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders"
    )
    product = models.ForeignKey(
        Product, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders"
    )
    fabric = models.ForeignKey(
        Fabric, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders"
    )

    total_quantity = models.PositiveIntegerField()
    size_breakdown = models.CharField(max_length=300, blank=True)

    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    advance_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    status = models.CharField(
        max_length=15, choices=OrderStatus.choices, default=OrderStatus.CONFIRMED
    )
    admin_notes = models.TextField(
        blank=True, help_text="Internal only -- never shown to the customer."
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders_created",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference_code} · {self.name}"

    @property
    def due_amount(self):
        if self.total_value is None:
            return None
        return self.total_value - self.advance_paid
