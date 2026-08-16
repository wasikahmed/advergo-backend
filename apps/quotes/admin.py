from django.contrib import admin, messages
from unfold.admin import ModelAdmin

from .models import QuoteRequest, QuoteRequestStatus
from .services import convert_quote_to_order


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
    fields = [*readonly_fields, "status", "admin_notes"]
    actions = ["convert_to_order"]

    @admin.action(description="Convert selected (reviewed) quotes into orders")
    def convert_to_order(self, request, queryset):
        created = 0
        for quote in queryset.exclude(status=QuoteRequestStatus.CONVERTED):
            convert_quote_to_order(quote, created_by=request.user)
            created += 1
        self.message_user(request, f"Created {created} order(s).", level=messages.SUCCESS)
