from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AchievementViewSet,
    BankAccountViewSet,
    BannerViewSet,
    ClientLogoViewSet,
    CompanyInfoView,
    GalleryCategoryViewSet,
    GalleryItemViewSet,
    HomeSectionBannerViewSet,
    MobileBankingAgentViewSet,
    ProcessStepViewSet,
    SocialLinkViewSet,
    StatViewSet,
    TeamMemberViewSet,
)

router = DefaultRouter()
router.register("banners", BannerViewSet, basename="banner")
router.register("section-banners", HomeSectionBannerViewSet, basename="section-banner")
router.register("stats", StatViewSet, basename="stat")
router.register("achievements", AchievementViewSet, basename="achievement")
router.register("clients", ClientLogoViewSet, basename="client-logo")
router.register("steps", ProcessStepViewSet, basename="process-step")
router.register("gallery-categories", GalleryCategoryViewSet, basename="gallery-category")
router.register("gallery", GalleryItemViewSet, basename="gallery-item")
router.register("team", TeamMemberViewSet, basename="team-member")
router.register("bank-accounts", BankAccountViewSet, basename="bank-account")
router.register("mobile-banking", MobileBankingAgentViewSet, basename="mobile-banking-agent")
router.register("social-links", SocialLinkViewSet, basename="social-link")

urlpatterns = [
    path("company/", CompanyInfoView.as_view(), name="company-info"),
    *router.urls,
]
