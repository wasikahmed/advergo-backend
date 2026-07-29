from decimal import Decimal

import pytest
from django.core import mail

from apps.invoices.models import Invoice
from apps.invoices.services import (
    create_or_update_invoice,
    generate_and_send_invoice,
    generate_invoice_number,
    render_invoice_pdf_bytes,
    send_invoice_email,
)
from apps.orders.models import Order

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


def test_generate_invoice_number_reuses_order_suffix(order):
    assert generate_invoice_number(order) == "INV-ABC12345"


def test_render_invoice_pdf_bytes_produces_a_real_pdf(order):
    pdf_bytes = render_invoice_pdf_bytes(order)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500


def test_create_or_update_invoice_saves_pdf_file(order):
    invoice = create_or_update_invoice(order)
    assert invoice.invoice_number == "INV-ABC12345"
    assert invoice.pdf_file.name
    assert invoice.order == order


def test_create_or_update_invoice_is_idempotent(order):
    first = create_or_update_invoice(order)
    second = create_or_update_invoice(order)
    assert first.id == second.id
    assert Invoice.objects.filter(order=order).count() == 1


def test_send_invoice_email_attaches_pdf(order):
    invoice = create_or_update_invoice(order)
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
    invoice = create_or_update_invoice(order)

    sent = send_invoice_email(order, invoice)
    assert sent is False
    assert len(mail.outbox) == 0


def test_generate_and_send_invoice_sets_sent_at(order):
    invoice = generate_and_send_invoice(order)
    assert invoice.sent_at is not None
    assert len(mail.outbox) == 1
