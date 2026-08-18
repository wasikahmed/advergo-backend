import base64
from functools import lru_cache

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

from apps.content.models import CompanyInfo

from .models import Chalan, Invoice, Quotation


def _get_company() -> CompanyInfo:
    company, _ = CompanyInfo.objects.get_or_create(
        pk=CompanyInfo.SINGLETON_ID, defaults={"name": "Advergo Sports & Fashion Wear Ltd."}
    )
    return company


@lru_cache(maxsize=1)
def _logo_data_uri() -> str:
    """
    Base64-inlined so WeasyPrint never has to resolve a URL or filesystem
    path for it -- it renders server-side with no request context, and
    static assets are served by Whitenoise/Cloudinary depending on
    environment, so a plain <img src="/static/..."> isn't reliably
    reachable from there. Cached: it's the same file on every PDF.
    """
    path = settings.BASE_DIR / "static" / "branding" / "logo.png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def _numbered(prefix: str, reference_code: str, order_prefix: str, existing_count: int) -> str:
    """First generation keeps the plain "<PREFIX>-<suffix>" number; every
    regeneration after that gets a "-R2", "-R3", ... suffix so each kept
    document has its own distinct, still-traceable number."""
    suffix = reference_code.removeprefix(order_prefix)
    base = f"{prefix}-{suffix}"
    return base if existing_count == 0 else f"{base}-R{existing_count + 1}"


def _render_pdf(template_name: str, context: dict) -> bytes:
    # Imported lazily: WeasyPrint needs system libs (Pango/Cairo) that aren't
    # installed everywhere this codebase might be imported (e.g. a bare test
    # collection step) -- only pay that cost when actually generating a PDF.
    from weasyprint import HTML

    html = render_to_string(template_name, context)
    return HTML(string=html).write_pdf()


# --- Invoice ---------------------------------------------------------------


def generate_invoice_number(order) -> str:
    return _numbered(
        "INV", order.reference_code, "ORD-", Invoice.objects.filter(order=order).count()
    )


def render_invoice_pdf_bytes(order, invoice_number: str | None = None) -> bytes:
    return _render_pdf(
        "invoices/invoice.html",
        {
            "order": order,
            "company": _get_company(),
            "logo_data_uri": _logo_data_uri(),
            "invoice_number": invoice_number or generate_invoice_number(order),
            "issued_date": timezone.now().strftime("%d %B, %Y"),
            "due_amount": order.due_amount,
        },
    )


def create_invoice(order, *, generated_by=None) -> Invoice:
    invoice_number = generate_invoice_number(order)
    pdf_bytes = render_invoice_pdf_bytes(order, invoice_number)
    invoice = Invoice(order=order, invoice_number=invoice_number, generated_by=generated_by)
    invoice.pdf_file.save(f"{invoice_number}.pdf", ContentFile(pdf_bytes), save=True)
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


def generate_and_send_invoice(order, *, generated_by=None) -> Invoice:
    invoice = create_invoice(order, generated_by=generated_by)
    if send_invoice_email(order, invoice):
        invoice.sent_at = timezone.now()
        invoice.save(update_fields=["sent_at"])
    return invoice


# --- Quotation ---------------------------------------------------------------


def generate_quotation_number(quote) -> str:
    return _numbered(
        "QUO", quote.reference_code, "QR-", Quotation.objects.filter(quote_request=quote).count()
    )


def render_quotation_pdf_bytes(quote, quotation_number: str | None = None) -> bytes:
    quoted_total = quote.quoted_price * quote.quantity if quote.quoted_price is not None else None
    return _render_pdf(
        "invoices/quotation.html",
        {
            "quote": quote,
            "company": _get_company(),
            "logo_data_uri": _logo_data_uri(),
            "quotation_number": quotation_number or generate_quotation_number(quote),
            "issued_date": timezone.now().strftime("%d %B, %Y"),
            "quoted_total": quoted_total,
        },
    )


def create_quotation(quote, *, generated_by=None) -> Quotation:
    quotation_number = generate_quotation_number(quote)
    pdf_bytes = render_quotation_pdf_bytes(quote, quotation_number)
    quotation = Quotation(
        quote_request=quote, quotation_number=quotation_number, generated_by=generated_by
    )
    quotation.pdf_file.save(f"{quotation_number}.pdf", ContentFile(pdf_bytes), save=True)
    return quotation


def send_quotation_email(quote, quotation) -> bool:
    if not quote.email:
        return False
    message = EmailMessage(
        subject=f"Your Advergo quotation {quotation.quotation_number}",
        body=(
            f"Hi {quote.name},\n\n"
            f"Please find attached your quotation ({quotation.quotation_number}) for request "
            f"{quote.reference_code}. Let us know if you'd like to proceed and our team will "
            "confirm details directly.\n\n"
            "Thank you for considering Advergo Sports & Fashion Wear Ltd."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[quote.email],
    )
    quotation.pdf_file.open("rb")
    try:
        message.attach(
            f"{quotation.quotation_number}.pdf", quotation.pdf_file.read(), "application/pdf"
        )
    finally:
        quotation.pdf_file.close()
    message.send()
    return True


def generate_and_send_quotation(quote, *, generated_by=None) -> Quotation:
    quotation = create_quotation(quote, generated_by=generated_by)
    if send_quotation_email(quote, quotation):
        quotation.sent_at = timezone.now()
        quotation.save(update_fields=["sent_at"])
    return quotation


# --- Chalan (delivery challan) ----------------------------------------------


def generate_chalan_number(order) -> str:
    return _numbered(
        "CHLN", order.reference_code, "ORD-", Chalan.objects.filter(order=order).count()
    )


def render_chalan_pdf_bytes(
    order, chalan_number: str | None = None, *, include_price: bool = False
) -> bytes:
    return _render_pdf(
        "invoices/chalan.html",
        {
            "order": order,
            "company": _get_company(),
            "logo_data_uri": _logo_data_uri(),
            "chalan_number": chalan_number or generate_chalan_number(order),
            "issued_date": timezone.now().strftime("%d %B, %Y"),
            "include_price": include_price,
        },
    )


def create_chalan(order, *, include_price: bool = False, generated_by=None) -> Chalan:
    chalan_number = generate_chalan_number(order)
    pdf_bytes = render_chalan_pdf_bytes(order, chalan_number, include_price=include_price)
    chalan = Chalan(
        order=order,
        chalan_number=chalan_number,
        include_price=include_price,
        generated_by=generated_by,
    )
    chalan.pdf_file.save(f"{chalan_number}.pdf", ContentFile(pdf_bytes), save=True)
    return chalan
