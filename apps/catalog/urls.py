from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, FabricViewSet, ProductViewSet, SizeChartRowViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("fabrics", FabricViewSet, basename="fabric")
router.register("products", ProductViewSet, basename="product")
router.register("size-chart", SizeChartRowViewSet, basename="size-chart-row")

urlpatterns = router.urls
