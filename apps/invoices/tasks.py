from celery import shared_task
from django.contrib.auth import get_user_model

from apps.orders.models import Order
from apps.quotes.models import QuoteRequest

from .services import create_chalan, generate_and_send_invoice, generate_and_send_quotation

User = get_user_model()


def _get_user(user_id):
    return User.objects.filter(id=user_id).first() if user_id else None


@shared_task
def generate_and_send_invoice_task(order_id, generated_by_id=None):
    order = Order.objects.get(id=order_id)
    invoice = generate_and_send_invoice(order, generated_by=_get_user(generated_by_id))
    return invoice.id


@shared_task
def generate_and_send_quotation_task(quote_id, generated_by_id=None):
    quote = QuoteRequest.objects.get(id=quote_id)
    quotation = generate_and_send_quotation(quote, generated_by=_get_user(generated_by_id))
    return quotation.id


@shared_task
def generate_chalan_task(order_id, include_price=False, generated_by_id=None):
    order = Order.objects.get(id=order_id)
    chalan = create_chalan(order, include_price=include_price, generated_by=_get_user(generated_by_id))
    return chalan.id
