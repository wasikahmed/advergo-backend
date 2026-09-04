from rest_framework.routers import DefaultRouter

from .views import ProductReviewViewSet, ReviewViewSet

router = DefaultRouter()
router.register("product", ProductReviewViewSet, basename="product-review")
router.register("", ReviewViewSet, basename="review")

urlpatterns = router.urls
