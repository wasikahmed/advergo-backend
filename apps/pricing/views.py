from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import PriceEstimateRequestSerializer, PriceEstimateResponseSerializer
from .services import estimate_price


class PriceEstimateView(APIView):
    """Public: live 'probable price' shown as the customer fills in the quote form."""

    permission_classes = [AllowAny]

    def post(self, request):
        request_serializer = PriceEstimateRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        estimate = estimate_price(**request_serializer.validated_data)

        response_serializer = PriceEstimateResponseSerializer(estimate.__dict__)
        return Response(response_serializer.data)
