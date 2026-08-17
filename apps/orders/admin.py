from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse
from django.urls import reverse
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action
from unfold.widgets import CHECKBOX_CLASSES

from apps.activity.services import log_activity
from apps.core.utils import admin_action_redirect
from apps.invoices.models import Chalan, Invoice

from .models import Order, OrderStatus


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


# Linear happy path -- CANCELLED is a side-branch handled separately, not
# part of "advance to next status".
_STATUS_PIPELINE = [
    OrderStatus.CONFIRMED,
    OrderStatus.IN_PRODUCTION,
    OrderStatus.QUALITY_CHECK,
    OrderStatus.READY,
    OrderStatus.DELIVERED,
]


class GenerateChalanForm(forms.Form):
    include_price = forms.BooleanField(
        required=False,
        label="Include unit price / total value",
        widget=forms.CheckboxInput(attrs={"class": " ".join(CHECKBOX_CLASSES)}),
    )

    def __init__(self, request, object_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)


@admin.register(Order)
class OrderAdmin(SimpleHistoryAdmin, ModelAdmin):
    # Kept short on purpose -- product/unit price/advance paid are one click
    # away on the detail page; a wider table just pushes the row-actions
    # menu off-screen. Hide/show more via the "Columns" toggle if needed.
    list_display = [
        "reference_code",
        "name",
        "total_quantity",
        "total_value",
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
    actions_row = [
        "preview_invoice_row",
        "preview_chalan_row",
        "advance_status_row",
        "cancel_order_row",
        "generate_invoice_row",
        "generate_chalan_row",
    ]
    # Same actions, available as buttons on the change form too -- staff
    # editing an order shouldn't have to go back to the changelist just to
    # preview or generate its documents.
    actions_detail = [
        "preview_invoice_row",
        "preview_chalan_row",
        "advance_status_row",
        "cancel_order_row",
        "generate_invoice_row",
        "generate_chalan_row",
    ]

    @action(description="Preview invoice PDF", icon="visibility", attrs={"target": "_blank"})
    def preview_invoice_row(self, request, object_id):
        from apps.invoices.services import render_invoice_pdf_bytes

        order = self.get_object(request, object_id)
        if order is None:
            return HttpResponse("Order not found.", status=404)
        response = HttpResponse(render_invoice_pdf_bytes(order), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{order.reference_code}-invoice-preview.pdf"'
        return response

    @action(description="Preview chalan PDF", icon="local_shipping", attrs={"target": "_blank"})
    def preview_chalan_row(self, request, object_id):
        from apps.invoices.services import render_chalan_pdf_bytes

        order = self.get_object(request, object_id)
        if order is None:
            return HttpResponse("Order not found.", status=404)
        response = HttpResponse(
            render_chalan_pdf_bytes(order, include_price=False), content_type="application/pdf"
        )
        response["Content-Disposition"] = f'inline; filename="{order.reference_code}-chalan-preview.pdf"'
        return response

    @action(description="Advance to next status", icon="arrow_forward")
    def advance_status_row(self, request, object_id):
        order = self.get_object(request, object_id)
        idx = _STATUS_PIPELINE.index(order.status) if order and order.status in _STATUS_PIPELINE else None
        if idx is None or idx + 1 >= len(_STATUS_PIPELINE):
            self.message_user(request, "This order can't be advanced further.", level=messages.WARNING)
        else:
            old_status = order.get_status_display()
            order.status = _STATUS_PIPELINE[idx + 1]
            order.save(update_fields=["status"])
            log_activity(
                actor=request.user,
                request=request,
                verb="advanced_status",
                target=order,
                description=f"{old_status} -> {order.get_status_display()}",
            )
            self.message_user(
                request,
                f"{order.reference_code} -> {order.get_status_display()}.",
                level=messages.SUCCESS,
            )
        return admin_action_redirect(request, reverse("admin:orders_order_changelist"))

    @action(description="Cancel order", icon="cancel")
    def cancel_order_row(self, request, object_id):
        order = self.get_object(request, object_id)
        if order is None or order.status == OrderStatus.CANCELLED:
            self.message_user(request, "Nothing to cancel.", level=messages.WARNING)
        else:
            order.status = OrderStatus.CANCELLED
            order.save(update_fields=["status"])
            log_activity(actor=request.user, request=request, verb="cancelled_order", target=order)
            self.message_user(request, f"{order.reference_code} cancelled.", level=messages.SUCCESS)
        return admin_action_redirect(request, reverse("admin:orders_order_changelist"))

    @admin.action(description="Generate PDF invoice and email to customer")
    def generate_and_send_invoice(self, request, queryset):
        from apps.invoices.services import generate_and_send_invoice as _generate

        sent, skipped = 0, 0
        for order in queryset:
            if order.total_value is None:
                skipped += 1
                continue
            invoice = _generate(order, generated_by=request.user)
            log_activity(
                actor=request.user,
                request=request,
                verb="generated_invoice",
                target=order,
                description=f"Generated invoice {invoice.invoice_number}",
            )
            sent += 1
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} order(s) with no total value set.",
                level=messages.WARNING,
            )
        self.message_user(request, f"Generated {sent} invoice(s).", level=messages.SUCCESS)

    @action(description="Generate invoice", icon="receipt_long")
    def generate_invoice_row(self, request, object_id):
        from apps.invoices.services import generate_and_send_invoice

        order = self.get_object(request, object_id)
        if order is None:
            self.message_user(request, "Order not found.", level=messages.ERROR)
        elif order.total_value is None:
            self.message_user(
                request, "Set a total value before generating an invoice.", level=messages.WARNING
            )
        else:
            invoice = generate_and_send_invoice(order, generated_by=request.user)
            log_activity(
                actor=request.user,
                request=request,
                verb="generated_invoice",
                target=order,
                description=f"Generated invoice {invoice.invoice_number}",
            )
            self.message_user(
                request, f"Generated invoice for {order.reference_code}.", level=messages.SUCCESS
            )
        return admin_action_redirect(request, reverse("admin:orders_order_changelist"))

    def _generate_chalan(self, request, queryset, *, include_price):
        from apps.invoices.services import create_chalan

        generated = 0
        for order in queryset:
            chalan = create_chalan(order, include_price=include_price, generated_by=request.user)
            log_activity(
                actor=request.user,
                request=request,
                verb="generated_chalan",
                target=order,
                description=f"Generated chalan {chalan.chalan_number}",
            )
            generated += 1
        self.message_user(request, f"Generated {generated} chalan(s).", level=messages.SUCCESS)

    @admin.action(description="Generate delivery chalan (no price)")
    def generate_chalan_without_price(self, request, queryset):
        self._generate_chalan(request, queryset, include_price=False)

    @admin.action(description="Generate delivery chalan (with price)")
    def generate_chalan_with_price(self, request, queryset):
        self._generate_chalan(request, queryset, include_price=True)

    @action(
        description="Generate chalan",
        icon="local_shipping",
        dialog={
            "title": "Generate delivery chalan",
            "description": "Choose whether this copy should also state price.",
            "form_class": GenerateChalanForm,
            "form_submit_text": "Generate",
        },
    )
    def generate_chalan_row(self, request, form, object_id):
        from apps.invoices.services import create_chalan

        order = self.get_object(request, object_id)
        if order is None:
            self.message_user(request, "Order not found.", level=messages.ERROR)
        else:
            chalan = create_chalan(
                order, include_price=form.cleaned_data["include_price"], generated_by=request.user
            )
            log_activity(
                actor=request.user,
                request=request,
                verb="generated_chalan",
                target=order,
                description=f"Generated chalan {chalan.chalan_number}",
            )
            self.message_user(
                request, f"Generated a chalan for {order.reference_code}.", level=messages.SUCCESS
            )
        return admin_action_redirect(request, reverse("admin:orders_order_changelist"))
