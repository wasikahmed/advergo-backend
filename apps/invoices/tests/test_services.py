from decimal import Decimal

import pytest
from django.core import mail

from apps.invoices.models import Chalan, Invoice, Quotation
from apps.invoices.services import (
    create_chalan,
    create_invoice,
    create_quotation,
    generate_and_send_invoice,
    generate_chalan_number,
    generate_invoice_number,
    generate_quotation_number,
    render_chalan_pdf_bytes,
    render_invoice_pdf_bytes,
    send_invoice_email,
)
from apps.orders.models import Order
from apps.quotes.models import QuoteRequest

pytestmark = pytest.mark.django_db


@pytest.fixture
def order():
    return Order.objects.create(
        reference_code="ORD-ABC12345",
        name="Rafiqul Islam",
        phone="0170000",
        email="rafiq@example.com",
        total_quantity=25,
        unit_price=Decimal("500.00"),
        total_value=Decimal("12500.00"),
        advance_paid=Decimal("2500.00"),
    )


@pytest.fixture
def quote():
    return QuoteRequest.objects.create(
        reference_code="QR-XYZ98765",
        name="Tanvir Hossain",
        phone="0180000",
        email="tanvir@example.com",
        quantity=30,
        estimated_price_low=Decimal("400.00"),
        estimated_price_high=Decimal("500.00"),
    )


# --- Invoice -----------------------------------------------------------------


def test_generate_invoice_number_reuses_order_suffix(order):
    assert generate_invoice_number(order) == "INV-ABC12345"


def test_render_invoice_pdf_bytes_produces_a_real_pdf(order):
    pdf_bytes = render_invoice_pdf_bytes(order)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500


def test_create_invoice_saves_pdf_file(order):
    invoice = create_invoice(order)
    assert invoice.invoice_number == "INV-ABC12345"
    assert invoice.pdf_file.name
    assert invoice.order == order


def test_create_invoice_keeps_history_instead_of_overwriting(order):
    first = create_invoice(order)
    second = create_invoice(order)

    assert first.id != second.id
    assert first.invoice_number == "INV-ABC12345"
    assert second.invoice_number == "INV-ABC12345-R2"
    assert Invoice.objects.filter(order=order).count() == 2


def test_send_invoice_email_attaches_pdf(order):
    invoice = create_invoice(order)
    sent = send_invoice_email(order, invoice)

    assert sent is True
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.to == ["rafiq@example.com"]
    assert len(email.attachments) == 1
    assert email.attachments[0][0] == "INV-ABC12345.pdf"


def test_send_invoice_email_skipped_without_customer_email(order):
    order.email = ""
    order.save(update_fields=["email"])
    invoice = create_invoice(order)

    sent = send_invoice_email(order, invoice)
    assert sent is False
    assert len(mail.outbox) == 0


def test_generate_and_send_invoice_sets_sent_at(order):
    invoice = generate_and_send_invoice(order)
    assert invoice.sent_at is not None
    assert len(mail.outbox) == 1


# --- Quotation -----------------------------------------------------------------


def test_generate_quotation_number_reuses_quote_suffix(quote):
    assert generate_quotation_number(quote) == "QUO-XYZ98765"


def test_create_quotation_prints_estimated_range_without_firm_price(quote):
    quotation = create_quotation(quote)
    assert quotation.quotation_number == "QUO-XYZ98765"
    assert quotation.pdf_file.name


def test_create_quotation_uses_firm_quoted_price_when_set(quote):
    quote.quoted_price = Decimal("450.00")
    quote.save(update_fields=["quoted_price"])
    quotation = create_quotation(quote)
    assert quotation.pdf_file.name


def test_create_quotation_keeps_history(quote):
    first = create_quotation(quote)
    second = create_quotation(quote)
    assert first.id != second.id
    assert second.quotation_number == "QUO-XYZ98765-R2"
    assert Quotation.objects.filter(quote_request=quote).count() == 2


# --- Chalan (delivery challan) -------------------------------------------------


def test_generate_chalan_number_reuses_order_suffix(order):
    assert generate_chalan_number(order) == "CHLN-ABC12345"


def test_render_chalan_pdf_bytes_without_price(order):
    pdf_bytes = render_chalan_pdf_bytes(order, include_price=False)
    assert pdf_bytes.startswith(b"%PDF")


def test_render_chalan_pdf_bytes_with_price(order):
    pdf_bytes = render_chalan_pdf_bytes(order, include_price=True)
    assert pdf_bytes.startswith(b"%PDF")


def test_create_chalan_defaults_to_no_price(order):
    chalan = create_chalan(order)
    assert chalan.include_price is False
    assert chalan.chalan_number == "CHLN-ABC12345"


def test_create_chalan_keeps_history(order):
    first = create_chalan(order, include_price=False)
    second = create_chalan(order, include_price=True)
    assert first.id != second.id
    assert second.chalan_number == "CHLN-ABC12345-R2"
    assert second.include_price is True
    assert Chalan.objects.filter(order=order).count() == 2
