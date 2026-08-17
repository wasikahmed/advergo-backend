from apps.core.utils import generate_reference_code

from .models import QuoteRequestStatus


def convert_quote_to_order(
    quote,
    created_by,
    *,
    total_quantity=None,
    size_breakdown=None,
    delivery_address=None,
    unit_price=None,
):
    """
    Staff-triggered: turn a reviewed QuoteRequest into a trackable Order. A
    quote rarely converts exactly as first asked -- price/quantity/size get
    negotiated -- so any of those can be overridden at conversion time; the
    QuoteRequest itself is never touched (it stays the frozen record of
    what was originally requested; the Order holds what was actually
    agreed). Local import avoids a module-level cycle -- apps.orders.models
    already imports apps.quotes.models for the QuoteRequest FK.
    """
    from apps.orders.models import Order

    final_quantity = total_quantity if total_quantity is not None else quote.quantity
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
        total_quantity=final_quantity,
        size_breakdown=size_breakdown if size_breakdown is not None else quote.size_breakdown,
        delivery_address=(
            delivery_address if delivery_address is not None else quote.delivery_address
        ),
        unit_price=unit_price,
        total_value=(unit_price * final_quantity) if unit_price is not None else None,
        created_by=created_by,
    )
    quote.status = QuoteRequestStatus.CONVERTED
    quote.save(update_fields=["status"])
    return order
