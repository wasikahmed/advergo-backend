from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.users import admin_2fa, admin_google, admin_views

api_v1_patterns = [
    path("auth/", include("apps.users.urls")),
    path("catalog/", include("apps.catalog.urls")),
    path("content/", include("apps.content.urls")),
    path("reviews/", include("apps.reviews.urls")),
    path("pricing/", include("apps.pricing.urls")),
    path("quotes/", include("apps.quotes.urls")),
    path("orders/", include("apps.orders.urls")),
    path("wishlist/", include("apps.wishlist.urls")),
]

urlpatterns = [
    # Must come before admin.site.urls: enables the "Forgotten your password?"
    # link on the admin login page (unfold's template only renders it if
    # 'admin_password_reset' resolves), and gives Django's classic
    # email-a-reset-link flow for admin accounts.
    path(
        f"{settings.ADMIN_URL}password_reset/",
        admin_views.AdminPasswordResetView.as_view(),
        name="admin_password_reset",
    ),
    path(
        f"{settings.ADMIN_URL}password_reset/done/",
        admin_views.AdminPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        admin_views.AdminPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        admin_views.AdminPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("admin-2fa/verify/", admin_2fa.verify, name="admin-2fa-verify"),
    path("admin-google-login/", admin_google.admin_google_login, name="admin-google-login"),
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/v1/", include(api_v1_patterns)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
