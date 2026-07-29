from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import ReadOnlyOrAdmin

from .filters import GalleryItemFilter
from .models import Achievement, Banner, ClientLogo, CompanyInfo, GalleryItem, ProcessStep, Stat
from .serializers import (
    AchievementSerializer,
    BannerSerializer,
    ClientLogoSerializer,
    CompanyInfoSerializer,
    GalleryItemSerializer,
    ProcessStepSerializer,
    StatSerializer,
)


class BannerViewSet(viewsets.ModelViewSet):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    permission_classes = [ReadOnlyOrAdmin]
    pagination_class = None

    @action(detail=False, methods=["get"])
    def active(self, request):
        banner = Banner.objects.active().first()
        if banner is None:
            return Response(None)
        return Response(self.get_serializer(banner).data)


class StatViewSet(viewsets.ModelViewSet):
    queryset = Stat.objects.all()
    serializer_class = StatSerializer
    permission_classes = [ReadOnlyOrAdmin]
    pagination_class = None


class AchievementViewSet(viewsets.ModelViewSet):
    queryset = Achievement.objects.all()
    serializer_class = AchievementSerializer
    permission_classes = [ReadOnlyOrAdmin]
    pagination_class = None


class ClientLogoViewSet(viewsets.ModelViewSet):
    queryset = ClientLogo.objects.all()
    serializer_class = ClientLogoSerializer
    permission_classes = [ReadOnlyOrAdmin]
    pagination_class = None


class ProcessStepViewSet(viewsets.ModelViewSet):
    queryset = ProcessStep.objects.all()
    serializer_class = ProcessStepSerializer
    permission_classes = [ReadOnlyOrAdmin]
    pagination_class = None


class GalleryItemViewSet(viewsets.ModelViewSet):
    queryset = GalleryItem.objects.all()
    serializer_class = GalleryItemSerializer
    permission_classes = [ReadOnlyOrAdmin]
    filterset_class = GalleryItemFilter
    pagination_class = None


class CompanyInfoView(generics.RetrieveUpdateAPIView):
    serializer_class = CompanyInfoSerializer
    permission_classes = [ReadOnlyOrAdmin]

    def get_object(self):
        obj, _ = CompanyInfo.objects.get_or_create(
            pk=1, defaults={"name": "Advergo Sports & Fashion Wear Ltd."}
        )
        return obj
