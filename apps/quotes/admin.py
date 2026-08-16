from django.contrib import admin, messages
from unfold.admin import ModelAdmin, TabularInline

from apps.invoices.models import Quotation

from .models import QuoteRequest, QuoteRequestStatus
from .services import convert_quote_to_order


class QuotationInline(TabularInline):
    model = Quotation
    extra = 0
    fields = ["quotation_number", "pdf_file", "generated_by", "sent_at", "created_at"]
    readonly_fields = fields
    can_delete = False
    ordering = ["-created_at"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(QuoteRequest)
class QuoteRequestAdmin(ModelAdmin):
    list_display = [
        "reference_code",
        "name",
        "phone",
        "product",
        "fabric",
        "quantity",
        "estimated_price_low",
        "estimated_price_high",
        "quoted_price",
        "status",
        "created_at",
    ]
    list_filter = ["status", "category"]
    list_editable = ["status"]
    search_fields = ["reference_code", "name", "phone", "email"]
    autocomplete_fields = ["category", "product", "fabric", "user"]
    readonly_fields = [
        "reference_code",
        "user",
        "name",
        "phone",
        "email",
        "category",
        "product",
        "fabric",
        "quantity",
        "size_breakdown",
        "delivery_address",
        "design_file",
        "notes",
        "estimated_price_low",
        "estimated_price_high",
        "created_at",
        "updated_at",
    ]
    fields = [*readonly_fields, "quoted_price", "status", "admin_notes"]
    inlines = [QuotationInline]
    actions = ["convert_to_order", "generate_and_send_quotation"]

    @admin.action(description="Convert selected (reviewed) quotes into orders")
    def convert_to_order(self, request, queryset):
        created = 0
        for quote in queryset.exclude(status=QuoteRequestStatus.CONVERTED):
            convert_quote_to_order(quote, created_by=request.user)
            created += 1
        self.message_user(request, f"Created {created} order(s).", level=messages.SUCCESS)

    @admin.action(description="Generate quotation PDF and email to customer")
    def generate_and_send_quotation(self, request, queryset):
        from apps.invoices.services import generate_and_send_quotation as _generate

        sent = 0
        for quote in queryset:
            _generate(quote, generated_by=request.user)
            sent += 1
        self.message_user(request, f"Generated {sent} quotation(s).", level=messages.SUCCESS)
