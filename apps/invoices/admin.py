from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from unfold.admin import ModelAdmin
from unfold.decorators import action

from apps.core.utils import admin_action_redirect

from .models import Chalan, Invoice, Quotation
from .services import create_chalan, generate_and_send_invoice, generate_and_send_quotation


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
    actions_row = ["view_pdf_row", "regenerate_row"]

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

    def has_view_pdf_row_permission(self, request, object_id=None) -> bool:
        if object_id is None:
            return True
        invoice = Invoice.objects.filter(pk=object_id).first()
        return bool(invoice and invoice.pdf_file)

    @action(description="View PDF", icon="visibility", attrs={"target": "_blank"})
    def view_pdf_row(self, request, object_id):
        invoice = self.get_object(request, object_id)
        if invoice is None or not invoice.pdf_file:
            self.message_user(request, "No PDF available.", level=messages.WARNING)
            return admin_action_redirect(request, reverse("admin:invoices_invoice_changelist"))
        return redirect(invoice.pdf_file.url)

    @action(description="Regenerate & resend", icon="refresh")
    def regenerate_row(self, request, object_id):
        invoice = self.get_object(request, object_id)
        if invoice is None:
            self.message_user(request, "Invoice not found.", level=messages.ERROR)
        else:
            generate_and_send_invoice(invoice.order, generated_by=request.user)
            self.message_user(
                request, f"Generated a new invoice for {invoice.order.reference_code}.", level=messages.SUCCESS
            )
        return admin_action_redirect(request, reverse("admin:invoices_invoice_changelist"))

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
    actions_row = ["view_pdf_row", "regenerate_row"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_pdf_row_permission(self, request, object_id=None) -> bool:
        if object_id is None:
            return True
        quotation = Quotation.objects.filter(pk=object_id).first()
        return bool(quotation and quotation.pdf_file)

    @action(description="View PDF", icon="visibility", attrs={"target": "_blank"})
    def view_pdf_row(self, request, object_id):
        quotation = self.get_object(request, object_id)
        if quotation is None or not quotation.pdf_file:
            self.message_user(request, "No PDF available.", level=messages.WARNING)
            return admin_action_redirect(request, reverse("admin:invoices_quotation_changelist"))
        return redirect(quotation.pdf_file.url)

    @action(description="Regenerate & resend", icon="refresh")
    def regenerate_row(self, request, object_id):
        quotation = self.get_object(request, object_id)
        if quotation is None:
            self.message_user(request, "Quotation not found.", level=messages.ERROR)
        else:
            generate_and_send_quotation(quotation.quote_request, generated_by=request.user)
            self.message_user(
                request,
                f"Generated a new quotation for {quotation.quote_request.reference_code}.",
                level=messages.SUCCESS,
            )
        return admin_action_redirect(request, reverse("admin:invoices_quotation_changelist"))

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
    actions_row = ["view_pdf_row", "regenerate_row"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_pdf_row_permission(self, request, object_id=None) -> bool:
        if object_id is None:
            return True
        chalan = Chalan.objects.filter(pk=object_id).first()
        return bool(chalan and chalan.pdf_file)

    @action(description="View PDF", icon="visibility", attrs={"target": "_blank"})
    def view_pdf_row(self, request, object_id):
        chalan = self.get_object(request, object_id)
        if chalan is None or not chalan.pdf_file:
            self.message_user(request, "No PDF available.", level=messages.WARNING)
            return admin_action_redirect(request, reverse("admin:invoices_chalan_changelist"))
        return redirect(chalan.pdf_file.url)

    @action(description="Regenerate (same price setting)", icon="refresh")
    def regenerate_row(self, request, object_id):
        chalan = self.get_object(request, object_id)
        if chalan is None:
            self.message_user(request, "Chalan not found.", level=messages.ERROR)
        else:
            create_chalan(chalan.order, include_price=chalan.include_price, generated_by=request.user)
            self.message_user(
                request, f"Generated a new chalan for {chalan.order.reference_code}.", level=messages.SUCCESS
            )
        return admin_action_redirect(request, reverse("admin:invoices_chalan_changelist"))

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
