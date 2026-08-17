from django.contrib import admin, messages
from django.urls import reverse
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action

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
    actions_row = ["advance_status_row", "cancel_order_row", "generate_invoice_row"]

    def has_advance_status_row_permission(self, request, object_id=None) -> bool:
        if object_id is None:
            return True
        order = Order.objects.filter(pk=object_id).first()
        return bool(
            order and order.status in _STATUS_PIPELINE and order.status != OrderStatus.DELIVERED
        )

    @action(description="Advance to next status", icon="arrow_forward", permissions=["advance_status_row"])
    def advance_status_row(self, request, object_id):
        order = self.get_object(request, object_id)
        idx = _STATUS_PIPELINE.index(order.status) if order and order.status in _STATUS_PIPELINE else None
        if idx is None or idx + 1 >= len(_STATUS_PIPELINE):
            self.message_user(request, "This order can't be advanced further.", level=messages.WARNING)
        else:
            order.status = _STATUS_PIPELINE[idx + 1]
            order.save(update_fields=["status"])
            self.message_user(
                request,
                f"{order.reference_code} -> {order.get_status_display()}.",
                level=messages.SUCCESS,
            )
        return admin_action_redirect(request, reverse("admin:orders_order_changelist"))

    def has_cancel_order_row_permission(self, request, object_id=None) -> bool:
        if object_id is None:
            return True
        order = Order.objects.filter(pk=object_id).first()
        return bool(order and order.status != OrderStatus.CANCELLED)

    @action(description="Cancel order", icon="cancel", permissions=["cancel_order_row"])
    def cancel_order_row(self, request, object_id):
        order = self.get_object(request, object_id)
        if order is None or order.status == OrderStatus.CANCELLED:
            self.message_user(request, "Nothing to cancel.", level=messages.WARNING)
        else:
            order.status = OrderStatus.CANCELLED
            order.save(update_fields=["status"])
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
            _generate(order, generated_by=request.user)
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
            generate_and_send_invoice(order, generated_by=request.user)
            self.message_user(
                request, f"Generated invoice for {order.reference_code}.", level=messages.SUCCESS
            )
        return admin_action_redirect(request, reverse("admin:orders_order_changelist"))

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
