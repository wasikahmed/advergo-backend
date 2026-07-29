from django.urls import path

from .views import PriceEstimateView

urlpatterns = [
    path("estimate/", PriceEstimateView.as_view(), name="pricing-estimate"),
]
