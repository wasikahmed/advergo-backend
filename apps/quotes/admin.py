from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse
from django.urls import reverse
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action
from unfold.widgets import INPUT_CLASSES

from apps.core.utils import admin_action_redirect, generate_reference_code
from apps.invoices.models import Quotation
from apps.pricing.services import estimate_price
from apps.users.services import get_or_create_guest_user

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


_input_attrs = {"class": " ".join(INPUT_CLASSES)}


class ConvertToOrderForm(forms.Form):
    """Pre-filled from the quote, but every value is editable -- a quote
    rarely converts exactly as first asked. The QuoteRequest itself is
    never touched by this; only the new Order gets these final values."""

    total_quantity = forms.IntegerField(min_value=1, label="Quantity", widget=forms.NumberInput(attrs=_input_attrs))
    size_breakdown = forms.CharField(
        required=False, label="Size breakdown", widget=forms.TextInput(attrs=_input_attrs)
    )
    unit_price = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        label="Unit price (৳)",
        widget=forms.NumberInput(attrs=_input_attrs),
    )
    delivery_address = forms.CharField(
        required=False, label="Delivery address", widget=forms.Textarea(attrs={**_input_attrs, "rows": 2})
    )

    def __init__(self, request, object_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if object_id and not self.is_bound:
            quote = QuoteRequest.objects.filter(pk=object_id).first()
            if quote:
                self.fields["total_quantity"].initial = quote.quantity
                self.fields["size_breakdown"].initial = quote.size_breakdown
                self.fields["unit_price"].initial = quote.quoted_price
                self.fields["delivery_address"].initial = quote.delivery_address


@admin.register(QuoteRequest)
class QuoteRequestAdmin(SimpleHistoryAdmin, ModelAdmin):
    """
    Most quotes arrive through the public website and are staff-reviewed
    here after the fact -- those customer-submitted fields stay locked once
    created, so the record shows exactly what was first asked for. But not
    every lead comes through the site (phone calls, social DMs), so staff
    can also create a quote from scratch: on Add, everything is editable;
    on Change, only quoted_price/status/admin_notes stay open, same as a
    website-submitted quote.
    """

    # Kept short on purpose -- product/fabric/estimated price are one click
    # away on the detail page; a wider table just pushes the row-actions
    # menu off-screen. Hide/show more via the "Columns" toggle if needed.
    list_display = [
        "reference_code",
        "name",
        "phone",
        "quantity",
        "quoted_price",
        "status",
        "created_at",
    ]
    list_filter = ["status", "category"]
    list_editable = ["status"]
    search_fields = ["reference_code", "name", "phone", "email"]
    autocomplete_fields = ["category", "product", "fabric", "design", "user"]
    inlines = [QuotationInline]
    actions = ["generate_and_send_quotation"]
    actions_row = ["preview_quotation_row", "convert_to_order_row"]

    _submitted_fields = [
        "user",
        "name",
        "phone",
        "email",
        "category",
        "product",
        "fabric",
        "design",
        "quantity",
        "size_breakdown",
        "delivery_address",
        "design_file",
        "notes",
    ]
    _locked_only_fields = ["reference_code", "estimated_price_low", "estimated_price_high"]

    def get_fields(self, request, obj=None):
        editable_tail = ["quoted_price", "status", "admin_notes"]
        if obj is None:
            # Staff entering a new lead -- everything except the
            # auto-generated reference/estimate is open.
            return [*self._submitted_fields, *editable_tail]
        return [*self._locked_only_fields, *self._submitted_fields, *editable_tail]

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
        return [*self._locked_only_fields, *self._submitted_fields, "created_at", "updated_at"]

    def save_model(self, request, obj, form, change):
        if not change:
            # Mirrors QuoteRequestCreateSerializer.create() -- staff-entered
            # leads get the same auto reference code, guest-account linking,
            # and price estimate a website submission would get.
            obj.reference_code = generate_reference_code("QR")
            if not obj.user_id:
                obj.user = get_or_create_guest_user(email=obj.email, phone=obj.phone)
            estimate = estimate_price(fabric=obj.fabric, category=obj.category, quantity=obj.quantity)
            obj.estimated_price_low = estimate.unit_price_low * obj.quantity
            obj.estimated_price_high = estimate.unit_price_high * obj.quantity
        super().save_model(request, obj, form, change)

    @action(description="Preview quotation PDF", icon="visibility", attrs={"target": "_blank"})
    def preview_quotation_row(self, request, object_id):
        from apps.invoices.services import render_quotation_pdf_bytes

        quote = self.get_object(request, object_id)
        if quote is None:
            return HttpResponse("Quote not found.", status=404)
        response = HttpResponse(render_quotation_pdf_bytes(quote), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{quote.reference_code}-preview.pdf"'
        return response

    def has_convert_to_order_row_permission(self, request, object_id=None) -> bool:
        if object_id is None:
            return True
        quote = QuoteRequest.objects.filter(pk=object_id).first()
        return bool(quote and quote.status != QuoteRequestStatus.CONVERTED)

    @action(
        description="Convert to order",
        icon="shopping_cart",
        permissions=["convert_to_order_row"],
        dialog={
            "title": "Convert to order",
            "description": "Adjust anything that changed since the quote was first submitted.",
            "form_class": ConvertToOrderForm,
            "form_submit_text": "Create order",
        },
    )
    def convert_to_order_row(self, request, form, object_id):
        quote = self.get_object(request, object_id)
        if quote is None or quote.status == QuoteRequestStatus.CONVERTED:
            self.message_user(request, "This quote was already converted.", level=messages.WARNING)
        else:
            order = convert_quote_to_order(
                quote,
                created_by=request.user,
                total_quantity=form.cleaned_data["total_quantity"],
                size_breakdown=form.cleaned_data["size_breakdown"],
                unit_price=form.cleaned_data["unit_price"],
                delivery_address=form.cleaned_data["delivery_address"],
            )
            self.message_user(
                request, f"Created order {order.reference_code}.", level=messages.SUCCESS
            )
        return admin_action_redirect(request, reverse("admin:quotes_quoterequest_changelist"))

    @admin.action(description="Generate quotation PDF and email to customer")
    def generate_and_send_quotation(self, request, queryset):
        from apps.invoices.services import generate_and_send_quotation as _generate

        sent = 0
        for quote in queryset:
            _generate(quote, generated_by=request.user)
            sent += 1
        self.message_user(request, f"Generated {sent} quotation(s).", level=messages.SUCCESS)
