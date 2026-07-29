from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.core.permissions import IsAdmin

from .models import QuoteRequest
from .serializers import QuoteRequestAdminSerializer, QuoteRequestCreateSerializer
from .services import convert_quote_to_order


class QuoteRequestViewSet(viewsets.ModelViewSet):
    """
    Public: submit a custom-quote request (POST only).
    Staff: list/view/update (status + admin_notes) via /admin/ or this API.
    """

    queryset = QuoteRequest.objects.select_related("category", "product", "fabric", "user")

    def get_serializer_class(self):
        return (
            QuoteRequestCreateSerializer if self.action == "create" else QuoteRequestAdminSerializer
        )

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        return [IsAdmin()]

    def get_throttles(self):
        if self.action == "create":
            self.throttle_scope = "quote_submit"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def convert_to_order(self, request, pk=None):
        """Staff action: after confirming terms by phone, turn a reviewed
        quote into a trackable Order."""
        from apps.orders.serializers import OrderFullSerializer

        order = convert_quote_to_order(self.get_object(), created_by=request.user)
        return Response(OrderFullSerializer(order).data, status=201)
