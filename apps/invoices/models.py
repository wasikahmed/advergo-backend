from django.db import models

from apps.core.models import TimeStampedModel
from apps.core.storage import get_raw_file_storage
from apps.orders.models import Order


class Invoice(TimeStampedModel):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="invoice")
    invoice_number = models.CharField(max_length=30, unique=True, editable=False)
    pdf_file = models.FileField(
        upload_to="invoices/", blank=True, null=True, storage=get_raw_file_storage
    )
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.invoice_number
