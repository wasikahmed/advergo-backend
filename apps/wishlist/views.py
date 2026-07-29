from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.catalog.models import Product

from .models import WishlistItem
from .serializers import WishlistItemSerializer


class WishlistItemViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = WishlistItemSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return WishlistItem.objects.filter(user=self.request.user).select_related(
            "product", "product__category"
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["post"])
    def toggle(self, request):
        product_id = request.data.get("product")
        product = Product.objects.filter(pk=product_id).first()
        if product is None:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        existing = WishlistItem.objects.filter(user=request.user, product=product).first()
        if existing:
            existing.delete()
            return Response({"wishlisted": False})

        WishlistItem.objects.create(user=request.user, product=product)
        return Response({"wishlisted": True}, status=status.HTTP_201_CREATED)
