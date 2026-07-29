from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

from apps.content.models import CompanyInfo

from .models import Invoice


def generate_invoice_number(order) -> str:
    # Order reference codes are "ORD-XXXXXXXX" -- reuse the suffix so the two
    # documents are visibly linked without a second random code.
    suffix = order.reference_code.removeprefix("ORD-")
    return f"INV-{suffix}"


def render_invoice_pdf_bytes(order) -> bytes:
    # Imported lazily: WeasyPrint needs system libs (Pango/Cairo) that aren't
    # installed everywhere this codebase might be imported (e.g. a bare test
    # collection step) -- only pay that cost when actually generating a PDF.
    from weasyprint import HTML

    company, _ = CompanyInfo.objects.get_or_create(
        pk=1, defaults={"name": "Advergo Sports & Fashion Wear Ltd."}
    )
    html = render_to_string(
        "invoices/invoice.html",
        {
            "order": order,
            "company": company,
            "invoice_number": generate_invoice_number(order),
            "issued_date": timezone.now().strftime("%d %B, %Y"),
            "due_amount": order.due_amount,
        },
    )
    return HTML(string=html).write_pdf()


def create_or_update_invoice(order) -> Invoice:
    invoice, _ = Invoice.objects.get_or_create(
        order=order, defaults={"invoice_number": generate_invoice_number(order)}
    )
    pdf_bytes = render_invoice_pdf_bytes(order)
    invoice.pdf_file.save(f"{invoice.invoice_number}.pdf", ContentFile(pdf_bytes), save=True)
    return invoice


def send_invoice_email(order, invoice) -> bool:
    if not order.email:
        return False
    message = EmailMessage(
        subject=f"Your Advergo invoice {invoice.invoice_number}",
        body=(
            f"Hi {order.name},\n\n"
            f"Please find attached your invoice ({invoice.invoice_number}) for order "
            f"{order.reference_code}. No online payment is required -- our team will "
            "follow up directly to settle any balance due.\n\n"
            "Thank you for choosing Advergo Sports & Fashion Wear Ltd."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.email],
    )
    invoice.pdf_file.open("rb")
    try:
        message.attach(f"{invoice.invoice_number}.pdf", invoice.pdf_file.read(), "application/pdf")
    finally:
        invoice.pdf_file.close()
    message.send()
    return True


def generate_and_send_invoice(order) -> Invoice:
    invoice = create_or_update_invoice(order)
    if send_invoice_email(order, invoice):
        invoice.sent_at = timezone.now()
        invoice.save(update_fields=["sent_at"])
    return invoice
