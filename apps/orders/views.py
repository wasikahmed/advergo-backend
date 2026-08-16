from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.utils import generate_reference_code

from .models import Order
from .permissions import CanManageOrders, is_accounts_full, is_accounts_limited, is_accounts_staff
from .serializers import OrderFullSerializer, OrderLimitedSerializer


class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManageOrders]

    def get_queryset(self):
        user = self.request.user
        base = Order.objects.select_related(
            "category", "product", "fabric", "customer", "quote_request"
        )
        if is_accounts_staff(user):
            return base
        return base.filter(customer=user)

    def get_serializer_class(self):
        user = self.request.user
        # AccountsLimited never sees pricing -- including on their own writes,
        # though CanManageOrders already blocks them from writing at all.
        if is_accounts_limited(user) and not is_accounts_full(user):
            return OrderLimitedSerializer
        return OrderFullSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, reference_code=generate_reference_code("ORD"))

    @action(detail=True, methods=["post"])
    def generate_invoice(self, request, pk=None):
        """Staff (Admin/AccountsFull) only -- AccountsLimited can view orders
        but never triggers a financial document. Runs as a background Celery
        task since PDF rendering + SMTP delivery shouldn't block the request."""
        if not is_accounts_full(request.user):
            return Response({"detail": "Not allowed."}, status=403)

        order = self.get_object()
        if order.total_value is None:
            return Response(
                {"detail": "Set a total value before generating an invoice."}, status=400
            )

        from apps.invoices.tasks import generate_and_send_invoice_task

        generate_and_send_invoice_task.delay(str(order.id), str(request.user.id))
        return Response({"detail": "Invoice generation started."}, status=202)

    @action(detail=True, methods=["post"])
    def generate_chalan(self, request, pk=None):
        """Staff (Admin/AccountsFull) only. Not emailed automatically -- a
        chalan travels with the physical shipment, so staff download and
        print/hand it over rather than send it electronically."""
        if not is_accounts_full(request.user):
            return Response({"detail": "Not allowed."}, status=403)

        order = self.get_object()
        # CamelCaseJSONParser already converts incoming keys to snake_case.
        include_price = bool(request.data.get("include_price", False))

        from apps.invoices.tasks import generate_chalan_task

        generate_chalan_task.delay(str(order.id), include_price, str(request.user.id))
        return Response({"detail": "Chalan generation started."}, status=202)
