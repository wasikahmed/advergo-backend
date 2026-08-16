from apps.core.utils import generate_reference_code

from .models import QuoteRequestStatus


def convert_quote_to_order(quote, created_by):
    """Staff-triggered: turn a reviewed QuoteRequest into a trackable Order.
    Local import avoids a module-level cycle -- apps.orders.models already
    imports apps.quotes.models for the QuoteRequest FK."""
    from apps.orders.models import Order

    order = Order.objects.create(
        reference_code=generate_reference_code("ORD"),
        quote_request=quote,
        customer=quote.user,
        name=quote.name,
        phone=quote.phone,
        email=quote.email,
        category=quote.category,
        product=quote.product,
        fabric=quote.fabric,
        design=quote.design,
        total_quantity=quote.quantity,
        size_breakdown=quote.size_breakdown,
        delivery_address=quote.delivery_address,
        created_by=created_by,
    )
    quote.status = QuoteRequestStatus.CONVERTED
    quote.save(update_fields=["status"])
    return order
