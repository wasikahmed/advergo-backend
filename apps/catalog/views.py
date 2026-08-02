from rest_framework import viewsets

from apps.core.permissions import ReadOnlyOrAdmin

from .filters import ProductFilter, SizeChartRowFilter
from .models import Category, Fabric, Product, SizeChartRow
from .serializers import (
    CategorySerializer,
    FabricSerializer,
    ProductSerializer,
    SizeChartRowSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [ReadOnlyOrAdmin]
    pagination_class = None


class FabricViewSet(viewsets.ModelViewSet):
    queryset = Fabric.objects.filter(deleted_at__isnull=True)
    serializer_class = FabricSerializer
    permission_classes = [ReadOnlyOrAdmin]
    pagination_class = None


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(deleted_at__isnull=True, is_active=True).select_related(
        "category"
    )
    serializer_class = ProductSerializer
    permission_classes = [ReadOnlyOrAdmin]
    filterset_class = ProductFilter
    pagination_class = None


class SizeChartRowViewSet(viewsets.ModelViewSet):
    queryset = SizeChartRow.objects.select_related("category")
    serializer_class = SizeChartRowSerializer
    permission_classes = [ReadOnlyOrAdmin]
    filterset_class = SizeChartRowFilter
    pagination_class = None
