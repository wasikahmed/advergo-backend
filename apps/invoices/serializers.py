from rest_framework import serializers

from .models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    pdf_file = serializers.FileField(use_url=True, read_only=True)

    class Meta:
        model = Invoice
        fields = ["id", "invoice_number", "pdf_file", "sent_at", "created_at"]
