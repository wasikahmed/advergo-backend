from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.core.storage import get_raw_file_storage
from apps.orders.models import Order
from apps.quotes.models import QuoteRequest


class Invoice(TimeStampedModel):
    """
    Every generation creates a new row rather than overwriting the last one
    -- regenerating an invoice (price correction, resend, ...) keeps a full
    history of what was actually issued and when, not just the latest copy.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="invoices")
    invoice_number = models.CharField(max_length=30, unique=True, editable=False)
    pdf_file = models.FileField(
        upload_to="advergo/invoices/", blank=True, null=True, storage=get_raw_file_storage
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.invoice_number


class Quotation(TimeStampedModel):
    """A formal price quotation PDF issued for a QuoteRequest -- same
    history-preserving shape as Invoice."""

    quote_request = models.ForeignKey(
        QuoteRequest, on_delete=models.CASCADE, related_name="quotations"
    )
    quotation_number = models.CharField(max_length=30, unique=True, editable=False)
    pdf_file = models.FileField(
        upload_to="advergo/quotations/", blank=True, null=True, storage=get_raw_file_storage
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.quotation_number


class Chalan(TimeStampedModel):
    """
    Delivery challan (চালান) -- accompanies the physical shipment as proof
    of a legitimate, traceable delivery (for the customer and, if the
    vehicle is stopped, for law enforcement). Deliberately separate from
    Invoice: whether it also states a price is a per-generation choice
    (`include_price`), not a fixed template difference.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="chalans")
    chalan_number = models.CharField(max_length=30, unique=True, editable=False)
    pdf_file = models.FileField(
        upload_to="advergo/chalans/", blank=True, null=True, storage=get_raw_file_storage
    )
    include_price = models.BooleanField(
        default=False, help_text="Whether this copy states unit price / total value."
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.chalan_number
