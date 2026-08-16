from django.contrib import admin, messages
from unfold.admin import ModelAdmin, TabularInline

from apps.invoices.models import Chalan, Invoice

from .models import Order


class InvoiceInline(TabularInline):
    model = Invoice
    extra = 0
    fields = ["invoice_number", "pdf_file", "generated_by", "sent_at", "created_at"]
    readonly_fields = fields
    can_delete = False
    ordering = ["-created_at"]

    def has_add_permission(self, request, obj=None):
        return False


class ChalanInline(TabularInline):
    model = Chalan
    extra = 0
    fields = ["chalan_number", "pdf_file", "include_price", "generated_by", "created_at"]
    readonly_fields = fields
    can_delete = False
    ordering = ["-created_at"]

    def has_add_permission(self, request, obj=None):
        return False


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
    inlines = [InvoiceInline, ChalanInline]
    actions = [
        "generate_and_send_invoice",
        "generate_chalan_without_price",
        "generate_chalan_with_price",
    ]

    @admin.action(description="Generate PDF invoice and email to customer")
    def generate_and_send_invoice(self, request, queryset):
        from apps.invoices.services import generate_and_send_invoice as _generate

        sent, skipped = 0, 0
        for order in queryset:
            if order.total_value is None:
                skipped += 1
                continue
            _generate(order, generated_by=request.user)
            sent += 1
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} order(s) with no total value set.",
                level=messages.WARNING,
            )
        self.message_user(request, f"Generated {sent} invoice(s).", level=messages.SUCCESS)

    def _generate_chalan(self, request, queryset, *, include_price):
        from apps.invoices.services import create_chalan

        generated = 0
        for order in queryset:
            create_chalan(order, include_price=include_price, generated_by=request.user)
            generated += 1
        self.message_user(request, f"Generated {generated} chalan(s).", level=messages.SUCCESS)

    @admin.action(description="Generate delivery chalan (no price)")
    def generate_chalan_without_price(self, request, queryset):
        self._generate_chalan(request, queryset, include_price=False)

    @admin.action(description="Generate delivery chalan (with price)")
    def generate_chalan_with_price(self, request, queryset):
        self._generate_chalan(request, queryset, include_price=True)
