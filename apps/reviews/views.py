from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle

from .models import ProductReview, Review, ReviewStatus
from .serializers import (
    ProductReviewCreateSerializer,
    ProductReviewSerializer,
    ReviewCreateSerializer,
    ReviewSerializer,
)


class ReviewViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Public: list approved reviews, submit a new one (goes to `pending` for
    admin moderation in /admin/ -- no public write access to `status`)."""

    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return Review.objects.filter(status=ReviewStatus.APPROVED)

    def get_serializer_class(self):
        return ReviewCreateSerializer if self.action == "create" else ReviewSerializer

    def get_throttles(self):
        if self.action == "create":
            self.throttle_scope = "review_submit"
            return [ScopedRateThrottle()]
        return super().get_throttles()


class ProductReviewViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Public: list a product's approved reviews (`?product=<id>`, required).
    Submitting one requires login -- one review per account per product,
    starts `pending` for the same admin moderation as general reviews."""

    pagination_class = None

    def get_queryset(self):
        queryset = ProductReview.objects.filter(status=ReviewStatus.APPROVED).select_related("user")
        product_id = self.request.query_params.get("product")
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def get_serializer_class(self):
        return ProductReviewCreateSerializer if self.action == "create" else ProductReviewSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_throttles(self):
        if self.action == "create":
            self.throttle_scope = "review_submit"
            return [ScopedRateThrottle()]
        return super().get_throttles()
