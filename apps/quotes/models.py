from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from apps.catalog.models import Category, Design, Fabric, Product
from apps.core.models import TimeStampedModel
from apps.core.storage import get_raw_file_storage
from apps.core.validators import validate_design_file


class QuoteRequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    REVIEWED = "reviewed", "Reviewed"
    QUOTED = "quoted", "Quoted"
    CONVERTED = "converted", "Converted to order"
    REJECTED = "rejected", "Rejected"


class QuoteRequest(TimeStampedModel):
    """
    A custom-order inquiry: fabric + size + design file, no payment collected here.
    Guest-submittable by design (only *placing a confirmed order* requires login,
    per spec) -- `user` is set automatically when the submitter happens to be
    logged in, but is never required.
    """

    reference_code = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quote_requests",
    )

    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quote_requests",
    )
    product = models.ForeignKey(
        Product, null=True, blank=True, on_delete=models.SET_NULL, related_name="quote_requests"
    )
    fabric = models.ForeignKey(
        Fabric, null=True, blank=True, on_delete=models.SET_NULL, related_name="quote_requests"
    )
    design = models.ForeignKey(
        Design,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quote_requests",
        help_text="Set when the customer picked a design from the catalog instead of "
        "uploading their own design_file.",
    )

    quantity = models.PositiveIntegerField()
    size_breakdown = models.CharField(
        max_length=300, blank=True, help_text="e.g. 5xS, 10xM, 8xL, 2xXL"
    )
    delivery_address = models.TextField(
        blank=True, help_text="Where the finished order should be delivered."
    )
    design_file = models.FileField(
        upload_to="advergo/quotes/",
        blank=True,
        null=True,
        validators=[validate_design_file],
        storage=get_raw_file_storage,
    )
    notes = models.TextField(blank=True)

    # Auto-computed at submission time via apps.pricing -- an indicative range,
    # not a final price (spec: no payment collected, staff confirms by phone).
    estimated_price_low = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    estimated_price_high = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    quoted_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Firm negotiated price staff enters before generating a formal Quotation "
        "PDF. Leave blank to have the PDF print the estimated range instead.",
    )

    status = models.CharField(
        max_length=12, choices=QuoteRequestStatus.choices, default=QuoteRequestStatus.PENDING
    )
    admin_notes = models.TextField(
        blank=True, help_text="Internal only -- never shown to the customer."
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference_code} · {self.name}"
