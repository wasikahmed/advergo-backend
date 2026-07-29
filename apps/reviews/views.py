from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle

from .models import Review, ReviewStatus
from .serializers import ReviewCreateSerializer, ReviewSerializer


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
