from django.contrib import admin, messages
from unfold.admin import ModelAdmin

from .models import Chalan, Invoice, Quotation
from .services import generate_and_send_invoice, generate_and_send_quotation, create_chalan


@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    list_display = ["invoice_number", "order", "generated_by", "sent_at", "created_at"]
    search_fields = ["invoice_number", "order__reference_code", "order__name"]
    autocomplete_fields = ["order"]
    readonly_fields = [
        "invoice_number",
        "pdf_file",
        "generated_by",
        "sent_at",
        "created_at",
        "updated_at",
    ]
    actions = ["regenerate_and_send"]

    def has_add_permission(self, request):
        # Only ever created via the generate action (renders the PDF, sets
        # the number) -- a blank "Add" form has nothing meaningful to fill in.
        return False

    def has_change_permission(self, request, obj=None):
        # Each row is a point-in-time record of what was actually issued --
        # regenerate via the action instead of editing one in place.
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Regenerate (new dated copy) and email to customer")
    def regenerate_and_send(self, request, queryset):
        orders = {invoice.order for invoice in queryset}
        for order in orders:
            generate_and_send_invoice(order, generated_by=request.user)
        self.message_user(request, f"Generated {len(orders)} new invoice(s).", level=messages.SUCCESS)


@admin.register(Quotation)
class QuotationAdmin(ModelAdmin):
    list_display = ["quotation_number", "quote_request", "generated_by", "sent_at", "created_at"]
    search_fields = ["quotation_number", "quote_request__reference_code", "quote_request__name"]
    autocomplete_fields = ["quote_request"]
    readonly_fields = [
        "quotation_number",
        "pdf_file",
        "generated_by",
        "sent_at",
        "created_at",
        "updated_at",
    ]
    actions = ["regenerate_and_send"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Regenerate (new dated copy) and email to customer")
    def regenerate_and_send(self, request, queryset):
        quotes = {quotation.quote_request for quotation in queryset}
        for quote in quotes:
            generate_and_send_quotation(quote, generated_by=request.user)
        self.message_user(request, f"Generated {len(quotes)} new quotation(s).", level=messages.SUCCESS)


@admin.register(Chalan)
class ChalanAdmin(ModelAdmin):
    list_display = ["chalan_number", "order", "include_price", "generated_by", "created_at"]
    search_fields = ["chalan_number", "order__reference_code", "order__name"]
    autocomplete_fields = ["order"]
    readonly_fields = [
        "chalan_number",
        "pdf_file",
        "include_price",
        "generated_by",
        "sent_at",
        "created_at",
        "updated_at",
    ]
    actions = ["regenerate_without_price", "regenerate_with_price"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _regenerate(self, request, queryset, *, include_price):
        orders = {chalan.order for chalan in queryset}
        for order in orders:
            create_chalan(order, include_price=include_price, generated_by=request.user)
        self.message_user(request, f"Generated {len(orders)} new chalan(s).", level=messages.SUCCESS)

    @admin.action(description="Regenerate (new dated copy) without price")
    def regenerate_without_price(self, request, queryset):
        self._regenerate(request, queryset, include_price=False)

    @admin.action(description="Regenerate (new dated copy) with price")
    def regenerate_with_price(self, request, queryset):
        self._regenerate(request, queryset, include_price=True)
