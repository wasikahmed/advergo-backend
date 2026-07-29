from django.contrib import admin, messages
from unfold.admin import ModelAdmin

from .models import Invoice
from .services import generate_and_send_invoice


@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    list_display = ["invoice_number", "order", "sent_at", "created_at"]
    search_fields = ["invoice_number", "order__reference_code", "order__name"]
    autocomplete_fields = ["order"]
    readonly_fields = ["invoice_number", "pdf_file", "sent_at", "created_at", "updated_at"]
    actions = ["regenerate_and_send"]

    @admin.action(description="Regenerate PDF and email to customer")
    def regenerate_and_send(self, request, queryset):
        sent = 0
        for invoice in queryset:
            generate_and_send_invoice(invoice.order)
            sent += 1
        self.message_user(request, f"Regenerated {sent} invoice(s).", level=messages.SUCCESS)
