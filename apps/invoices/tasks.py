from celery import shared_task

from apps.orders.models import Order

from .services import generate_and_send_invoice


@shared_task
def generate_and_send_invoice_task(order_id):
    order = Order.objects.get(id=order_id)
    invoice = generate_and_send_invoice(order)
    return invoice.id
