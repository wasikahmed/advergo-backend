from rest_framework import viewsets

from apps.core.permissions import ReadOnlyOrAdmin

from .filters import DesignFilter, ProductFilter, SizeChartRowFilter
from .models import Category, Design, Fabric, Product, SizeChartRow
from .serializers import (
    CategorySerializer,
    DesignSerializer,
    FabricSerializer,
    ProductSerializer,
    SizeChartRowSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    List returns only top-level categories (each with its subcategories
    nested under `children`) -- that's what the homepage and /categories
    page need. Retrieve-by-slug works for any node, top-level or
    subcategory, so a subcategory's own page can fetch its name/image too.
    """

    serializer_class = CategorySerializer
    permission_classes = [ReadOnlyOrAdmin]
    pagination_class = None
    lookup_field = "slug"

    def get_queryset(self):
        queryset = Category.objects.prefetch_related("children")
        if self.action == "list":
            queryset = queryset.filter(parent__isnull=True)
        return queryset


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


class DesignViewSet(viewsets.ModelViewSet):
    queryset = Design.objects.filter(deleted_at__isnull=True, is_active=True).select_related(
        "category"
    )
    serializer_class = DesignSerializer
    permission_classes = [ReadOnlyOrAdmin]
    filterset_class = DesignFilter
