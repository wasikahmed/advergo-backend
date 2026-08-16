from django.contrib import admin, messages
from unfold.admin import ModelAdmin

from .models import Order


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = [
        "reference_code",
        "name",
        "product",
        "total_quantity",
        "unit_price",
        "total_value",
        "advance_paid",
        "status",
        "created_at",
    ]
    list_filter = ["status", "category"]
    list_editable = ["status"]
    search_fields = ["reference_code", "name", "phone", "email"]
    autocomplete_fields = [
        "category",
        "product",
        "fabric",
        "customer",
        "quote_request",
        "created_by",
    ]
    readonly_fields = ["reference_code", "created_by", "created_at", "updated_at"]
    actions = ["generate_and_send_invoice"]

    @admin.action(description="Generate PDF invoice and email to customer")
    def generate_and_send_invoice(self, request, queryset):
        from apps.invoices.services import generate_and_send_invoice as _generate

        sent, skipped = 0, 0
        for order in queryset:
            if order.total_value is None:
                skipped += 1
                continue
            _generate(order)
            sent += 1
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} order(s) with no total value set.",
                level=messages.WARNING,
            )
        self.message_user(request, f"Generated {sent} invoice(s).", level=messages.SUCCESS)
