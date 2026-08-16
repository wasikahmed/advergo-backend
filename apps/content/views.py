from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import ReadOnlyOrAdmin

from .filters import GalleryItemFilter
from .models import (
    Achievement,
    BankAccount,
    Banner,
    ClientLogo,
    CompanyInfo,
    GalleryCategory,
    GalleryItem,
    MobileBankingAgent,
    ProcessStep,
    Stat,
    TeamMember,
)
from .serializers import (
    AchievementSerializer,
    BankAccountSerializer,
    BannerSerializer,
    ClientLogoSerializer,
    CompanyInfoSerializer,
    GalleryCategorySerializer,
    GalleryItemSerializer,
    MobileBankingAgentSerializer,
    ProcessStepSerializer,
    StatSerializer,
    TeamMemberSerializer,
)


class BannerViewSet(viewsets.ModelViewSet):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    permission_classes = [ReadOnlyOrAdmin]
    pagination_class = None

    @action(detail=False, methods=["get"])
    def active(self, request):
        banners = Banner.objects.active()
        return Response(self.get_serializer(banners, many=True).data)


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


class GalleryCategoryViewSet(viewsets.ModelViewSet):
    queryset = GalleryCategory.objects.all()
    serializer_class = GalleryCategorySerializer
    permission_classes = [ReadOnlyOrAdmin]
    pagination_class = None


class GalleryItemViewSet(viewsets.ModelViewSet):
    queryset = GalleryItem.objects.select_related("category").all()
    serializer_class = GalleryItemSerializer
    permission_classes = [ReadOnlyOrAdmin]
    filterset_class = GalleryItemFilter
    pagination_class = None


class TeamMemberViewSet(viewsets.ModelViewSet):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer
    permission_classes = [ReadOnlyOrAdmin]
    pagination_class = None


class BankAccountViewSet(viewsets.ModelViewSet):
    queryset = BankAccount.objects.all()
    serializer_class = BankAccountSerializer
    permission_classes = [ReadOnlyOrAdmin]
    pagination_class = None


class MobileBankingAgentViewSet(viewsets.ModelViewSet):
    queryset = MobileBankingAgent.objects.all()
    serializer_class = MobileBankingAgentSerializer
    permission_classes = [ReadOnlyOrAdmin]
    pagination_class = None


class CompanyInfoView(generics.RetrieveUpdateAPIView):
    serializer_class = CompanyInfoSerializer
    permission_classes = [ReadOnlyOrAdmin]

    def get_object(self):
        obj, _ = CompanyInfo.objects.get_or_create(
            pk=CompanyInfo.SINGLETON_ID, defaults={"name": "Advergo Sports & Fashion Wear Ltd."}
        )
        return obj
