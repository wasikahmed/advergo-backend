from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AchievementViewSet,
    BannerViewSet,
    ClientLogoViewSet,
    CompanyInfoView,
    GalleryItemViewSet,
    ProcessStepViewSet,
    StatViewSet,
)

router = DefaultRouter()
router.register("banners", BannerViewSet, basename="banner")
router.register("stats", StatViewSet, basename="stat")
router.register("achievements", AchievementViewSet, basename="achievement")
router.register("clients", ClientLogoViewSet, basename="client-logo")
router.register("steps", ProcessStepViewSet, basename="process-step")
router.register("gallery", GalleryItemViewSet, basename="gallery-item")

urlpatterns = [
    path("company/", CompanyInfoView.as_view(), name="company-info"),
    *router.urls,
]
