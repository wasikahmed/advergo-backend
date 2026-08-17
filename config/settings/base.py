from datetime import timedelta
from pathlib import Path

import environ
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# Mount point for the Django admin. Defaults to "admin/" for local dev
# convenience; production sets ADMIN_URL to a non-guessable slug via .env.prod
# so the admin isn't sitting at the first path any scanner tries.
ADMIN_URL = env("ADMIN_URL", default="admin/")
# Only staff use any login form in this project (customers authenticate via
# the JWT API instead) -- point Django's own LOGIN_URL default at the admin
# login rather than the nonexistent /accounts/login/, since PasswordReset*
# views resolve their own login links from this.
LOGIN_URL = "admin:login"
# Django's own default (/accounts/profile/) 404s here -- only matters when a
# login form is submitted with no explicit ?next=, e.g. hitting /admin/login/
# directly rather than being redirected there from a protected page.
LOGIN_REDIRECT_URL = "admin:index"

DJANGO_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "cloudinary",
]
# Deliberately NOT registering "cloudinary_storage" as an app: its storage
# classes (MediaCloudinaryStorage, RawMediaCloudinaryStorage -- used below by
# get_raw_file_storage()) are plain classes imported by dotted path and don't
# need app registration to work. Registering the app also installs its
# `collectstatic` override, which is a deliberate no-op for any file unless
# STATICFILES_STORAGE is *their* StaticCloudinaryStorage -- since we don't use
# Cloudinary for static files (see STORAGES below), that override silently
# collects nothing. Found by actually running collectstatic in the prod
# image and reading django-cloudinary-storage's source, not the docs.

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "simple_history",
]

LOCAL_APPS = [
    "apps.core",
    "apps.users",
    "apps.access_control",
    "apps.catalog",
    "apps.content",
    "apps.reviews",
    "apps.pricing",
    "apps.quotes",
    "apps.orders",
    "apps.invoices",
    "apps.wishlist",
    "apps.activity",
]

# django_cleanup must load last -- it walks every already-registered model's
# FileField/ImageField to hook deletion signals, so any app after it in this
# list would be missed. Deletes the *old* file from storage (Cloudinary in
# prod) when a FileField/ImageField value is replaced or the row is deleted;
# without it, replacing/deleting an image just orphans the old blob forever.
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS + ["django_cleanup.apps.CleanupConfig"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.users.admin_2fa_middleware.AdminTwoFactorMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Populates HistoricalRecords.history_user automatically from the
    # request -- without this, every .save() needs _history_user set by hand.
    "simple_history.middleware.HistoryRequestMiddleware",
]

# Django's SecurityMiddleware default ("same-origin") severs window.opener
# on any popup the page opens -- which breaks the admin's Google Sign-In
# button, since Google's popup relays the credential back via that
# reference once you pick an account. "same-origin-allow-popups" keeps the
# same cross-origin isolation otherwise, it just lets popups we open keep
# their opener link (Google's own documented fix for this exact symptom:
# the popup opens, the account picker works, then it hangs).
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.google_client_id",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

AUTH_USER_MODEL = "users.User"
AUTHENTICATION_BACKENDS = ["apps.users.backends.EmailOrPhoneBackend"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Admin branding assets (logo/icon/favicon) live here, outside any app.
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Plain storage -- no build-time compression/manifest post_process step.
    # WhiteNoiseMiddleware (already in MIDDLEWARE) still serves these
    # efficiently at runtime with on-the-fly gzip + sensible cache headers.
    # Deliberate, not a default we forgot to upgrade: django-unfold's bundled
    # static assets (font CSS, then separately a vendored Alpine.js LICENSE
    # file) broke *two different* WhiteNoise post_process storage classes in
    # a row with unrelated-looking errors -- both reproduced from a
    # completely fresh STATIC_ROOT, so it's those assets tripping up
    # WhiteNoise's post-processing, not stale state or a config mistake on
    # our side. Found by actually running collectstatic in the prod image
    # against real files, not by reading the docs.
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
# django-cloudinary-storage's `collectstatic` override (installed because
# `cloudinary_storage` is in INSTALLED_APPS for *media*) still reads the
# pre-Django-4.2 STATICFILES_STORAGE setting and crashes with an
# AttributeError if it's absent. We use STORAGES, not this, but keep it in
# sync as a compatibility shim for that one package.
STATICFILES_STORAGE = STORAGES["staticfiles"]["BACKEND"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# --- Media storage (Cloudinary) ---------------------------------------------
# Falls back to local disk (STORAGES["default"] above) until credentials are
# set, so the project works out of the box before a Cloudinary account exists.
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": env("CLOUDINARY_CLOUD_NAME", default=""),
    "API_KEY": env("CLOUDINARY_API_KEY", default=""),
    "API_SECRET": env("CLOUDINARY_API_SECRET", default=""),
}
# Single source of truth for "are we using Cloudinary right now" -- both
# STORAGES["default"] below and apps.core.storage.get_raw_file_storage()
# key off this, so config.settings.test can flip one flag and be sure
# nothing (including raw/PDF uploads) reaches the real Cloudinary API.
USE_CLOUDINARY = bool(CLOUDINARY_STORAGE["CLOUD_NAME"])
if USE_CLOUDINARY:
    STORAGES["default"] = {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- REST framework -----------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Deny by default; individual views opt into AllowAny for public reads.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    # camelCase in/out so responses match the frontend's TS types (fabric.bestFor,
    # product.reviewCount, ...) with no manual field-mapping layer on the frontend.
    "DEFAULT_RENDERER_CLASSES": [
        "djangorestframework_camel_case.render.CamelCaseJSONRenderer",
        "djangorestframework_camel_case.render.CamelCaseBrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "djangorestframework_camel_case.parser.CamelCaseJSONParser",
        "djangorestframework_camel_case.parser.CamelCaseMultiPartParser",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # Public browsing fans out into several parallel GETs per page (categories,
        # products, stats, gallery, company, ...) -- this is a ceiling against
        # scraping/abuse, not a per-page-load budget. 60/min proved too tight in
        # practice: a couple of real navigations tripped it. Write endpoints that
        # actually need tight limits (quote/review submission) get their own scope.
        "anon": "600/min",
        "user": "600/min",
        "quote_submit": "10/hour",
        "review_submit": "5/hour",
        "otp_verify": "10/hour",
        "otp_request": "5/hour",
        "password_reset": "5/hour",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Advergo API",
    "DESCRIPTION": "Catalog, custom quotes, orders, and invoicing for Advergo Sports & Fashion Wear Ltd.",  # noqa: E501
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --- CORS -----------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# --- Celery -----------------------------------------------------------------
CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# --- Cache (also backs DRF's rate throttles and apps.users.otp) -------------
# Separate Redis DB index from the Celery broker above so cache keys and
# broker/queue data don't share a keyspace.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_CACHE_URL", default="redis://localhost:6379/1"),
    }
}

# --- Email ------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Advergo <no-reply@advergo.com>")

# --- Auth-adjacent -----------------------------------------------------------
# Base URL of the frontend app, used to build links sent in emails (password
# reset, staff invites).
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")
# OAuth 2.0 client ID (Web application type) from Google Cloud Console,
# used to verify the ID token the frontend gets from Google Sign-In.
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")

# --- Geolocation (login history "location" column) --------------------------
# MaxMind's GeoLite2-City.mmdb, downloaded via `manage.py download_geoip_db`
# (needs a free MaxMind account + license key -- see that command's help
# text). Location resolution degrades to blank if this file isn't present,
# same as any other IP that can't be resolved.
MAXMIND_LICENSE_KEY = env("MAXMIND_LICENSE_KEY", default="")
GEOIP_PATH = env("GEOIP_PATH", default=str(BASE_DIR / "geoip" / "GeoLite2-City.mmdb"))

# --- File upload limits -----------------------------------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20 MB, matches quote-form spec
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

# --- Unfold (admin theme) ---------------------------------------------------
# Branding assets live in static/branding/ (cropped from the frontend's own
# logo-header.png so the admin matches the storefront instead of Unfold's
# default look).


def _nav_permission(codename):
    """
    Gates a SIDEBAR nav item on a real Django permission (app_label.view_x),
    not just is_staff -- Unfold hides the item's <li> when this returns False,
    and its own template CSS (has-[ol]:has-[li]:block) collapses the whole
    section header/separator too once every item in it is hidden, so a role
    with no permissions in a section never sees that section at all.
    """
    return lambda request: request.user.has_perm(codename)


UNFOLD = {
    "SITE_TITLE": "Advergo Admin",
    "SITE_HEADER": "Advergo Sports & Fashion Wear Ltd.",
    "DASHBOARD_CALLBACK": "apps.core.dashboard.dashboard_callback",
    "SITE_LOGO": {
        "light": lambda request: static("branding/logo.png"),
        "dark": lambda request: static("branding/logo-dark.png"),
    },
    "SITE_ICON": lambda request: static("branding/icon.png"),
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "180x180",
            "type": "image/png",
            "href": lambda request: static("branding/favicon.png"),
        },
    ],
    # Swap Unfold's default violet accent for the storefront's brand red
    # (same hex values as --color-brand-red/-dark/-deep in the frontend).
    "STYLES": [
        lambda request: static("admin/css/column-controls.css"),
    ],
    "SCRIPTS": [
        lambda request: static("admin/js/column-controls.js"),
        lambda request: static("admin/js/user-autocomplete.js"),
    ],
    # Setting this list at all replaces Unfold's default "Change password"
    # link in the account dropdown rather than adding alongside it, so it
    # has to be listed explicitly here too.
    "ACCOUNT": {
        "navigation": [
            {"title": _("My profile"), "link": reverse_lazy("admin-profile")},
            {"title": _("Change password"), "link": reverse_lazy("admin:password_change")},
        ],
    },
    "COLORS": {
        "primary": {
            "50": "#fdf2f2",
            "100": "#fbdfe0",
            "200": "#f5b8ba",
            "300": "#ee8b8e",
            "400": "#e35a5f",
            "500": "#c8262c",
            "600": "#a91218",
            "700": "#8a0f14",
            "800": "#6b0c10",
            "900": "#4a0a0d",
            "950": "#2e0608",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": None,
                "collapsible": False,
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            {
                "title": _("Sales"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Quote requests"),
                        "icon": "request_quote",
                        "link": reverse_lazy("admin:quotes_quoterequest_changelist"),
                        "permission": _nav_permission("quotes.view_quoterequest"),
                    },
                    {
                        "title": _("Orders"),
                        "icon": "shopping_cart",
                        "link": reverse_lazy("admin:orders_order_changelist"),
                        "permission": _nav_permission("orders.view_order"),
                    },
                ],
            },
            {
                "title": _("Documents"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Invoices"),
                        "icon": "receipt_long",
                        "link": reverse_lazy("admin:invoices_invoice_changelist"),
                        "permission": _nav_permission("invoices.view_invoice"),
                    },
                    {
                        "title": _("Quotations"),
                        "icon": "description",
                        "link": reverse_lazy("admin:invoices_quotation_changelist"),
                        "permission": _nav_permission("invoices.view_quotation"),
                    },
                    {
                        "title": _("Chalans"),
                        "icon": "local_shipping",
                        "link": reverse_lazy("admin:invoices_chalan_changelist"),
                        "permission": _nav_permission("invoices.view_chalan"),
                    },
                ],
            },
            {
                "title": _("Catalog"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Categories"),
                        "icon": "category",
                        "link": reverse_lazy("admin:catalog_category_changelist"),
                        "permission": _nav_permission("catalog.view_category"),
                    },
                    {
                        "title": _("Products"),
                        "icon": "inventory_2",
                        "link": reverse_lazy("admin:catalog_product_changelist"),
                        "permission": _nav_permission("catalog.view_product"),
                    },
                    {
                        "title": _("Fabrics"),
                        "icon": "texture",
                        "link": reverse_lazy("admin:catalog_fabric_changelist"),
                        "permission": _nav_permission("catalog.view_fabric"),
                    },
                    {
                        "title": _("Designs"),
                        "icon": "palette",
                        "link": reverse_lazy("admin:catalog_design_changelist"),
                        "permission": _nav_permission("catalog.view_design"),
                    },
                    {
                        "title": _("Size chart rows"),
                        "icon": "straighten",
                        "link": reverse_lazy("admin:catalog_sizechartrow_changelist"),
                        "permission": _nav_permission("catalog.view_sizechartrow"),
                    },
                ],
            },
            {
                "title": _("Pricing"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Fabric price rules"),
                        "icon": "payments",
                        "link": reverse_lazy("admin:pricing_fabricpricerule_changelist"),
                        "permission": _nav_permission("pricing.view_fabricpricerule"),
                    },
                    {
                        "title": _("Category price rules"),
                        "icon": "payments",
                        "link": reverse_lazy("admin:pricing_categorypricerule_changelist"),
                        "permission": _nav_permission("pricing.view_categorypricerule"),
                    },
                    {
                        "title": _("Quantity discount tiers"),
                        "icon": "percent",
                        "link": reverse_lazy("admin:pricing_quantitydiscounttier_changelist"),
                        "permission": _nav_permission("pricing.view_quantitydiscounttier"),
                    },
                ],
            },
            {
                "title": _("Site content"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Banners"),
                        "icon": "view_carousel",
                        "link": reverse_lazy("admin:content_banner_changelist"),
                        "permission": _nav_permission("content.view_banner"),
                    },
                    {
                        "title": _("Home section banners"),
                        "icon": "view_carousel",
                        "link": reverse_lazy("admin:content_homesectionbanner_changelist"),
                        "permission": _nav_permission("content.view_homesectionbanner"),
                    },
                    {
                        "title": _("Stats"),
                        "icon": "bar_chart",
                        "link": reverse_lazy("admin:content_stat_changelist"),
                        "permission": _nav_permission("content.view_stat"),
                    },
                    {
                        "title": _("Achievements"),
                        "icon": "military_tech",
                        "link": reverse_lazy("admin:content_achievement_changelist"),
                        "permission": _nav_permission("content.view_achievement"),
                    },
                    {
                        "title": _("Client logos"),
                        "icon": "business",
                        "link": reverse_lazy("admin:content_clientlogo_changelist"),
                        "permission": _nav_permission("content.view_clientlogo"),
                    },
                    {
                        "title": _("Team members"),
                        "icon": "groups",
                        "link": reverse_lazy("admin:content_teammember_changelist"),
                        "permission": _nav_permission("content.view_teammember"),
                    },
                    {
                        "title": _("Bank accounts"),
                        "icon": "account_balance",
                        "link": reverse_lazy("admin:content_bankaccount_changelist"),
                        "permission": _nav_permission("content.view_bankaccount"),
                    },
                    {
                        "title": _("Mobile banking agents"),
                        "icon": "smartphone",
                        "link": reverse_lazy("admin:content_mobilebankingagent_changelist"),
                        "permission": _nav_permission("content.view_mobilebankingagent"),
                    },
                    {
                        "title": _("Official documents"),
                        "icon": "gavel",
                        "link": reverse_lazy("admin:content_officialdocument_changelist"),
                        "permission": _nav_permission("content.view_officialdocument"),
                    },
                    {
                        "title": _("Process steps"),
                        "icon": "linear_scale",
                        "link": reverse_lazy("admin:content_processstep_changelist"),
                        "permission": _nav_permission("content.view_processstep"),
                    },
                    {
                        "title": _("Gallery categories"),
                        "icon": "collections",
                        "link": reverse_lazy("admin:content_gallerycategory_changelist"),
                        "permission": _nav_permission("content.view_gallerycategory"),
                    },
                    {
                        "title": _("Gallery items"),
                        "icon": "photo_library",
                        "link": reverse_lazy("admin:content_galleryitem_changelist"),
                        "permission": _nav_permission("content.view_galleryitem"),
                    },
                    {
                        "title": _("Company info"),
                        "icon": "info",
                        "link": reverse_lazy("admin:content_companyinfo_changelist"),
                        "permission": _nav_permission("content.view_companyinfo"),
                    },
                ],
            },
            {
                "title": _("Customers"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Reviews"),
                        "icon": "reviews",
                        "link": reverse_lazy("admin:reviews_review_changelist"),
                        "permission": _nav_permission("reviews.view_review"),
                    },
                    {
                        "title": _("Wishlist items"),
                        "icon": "favorite",
                        "link": reverse_lazy("admin:wishlist_wishlistitem_changelist"),
                        "permission": _nav_permission("wishlist.view_wishlistitem"),
                    },
                ],
            },
            {
                "title": _("Access control"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "group",
                        "link": reverse_lazy("admin:users_user_changelist"),
                        "permission": _nav_permission("users.view_user"),
                    },
                    {
                        "title": _("Staff invites"),
                        "icon": "mail",
                        "link": reverse_lazy("admin:users_staffinvite_changelist"),
                        "permission": _nav_permission("users.view_staffinvite"),
                    },
                    {
                        "title": _("Roles"),
                        "icon": "admin_panel_settings",
                        "link": reverse_lazy("admin:access_control_role_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
            {
                "title": _("Activity"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Login history"),
                        "icon": "history",
                        "link": reverse_lazy("admin:activity_loginevent_changelist"),
                        "permission": _nav_permission("activity.view_loginevent"),
                    },
                    {
                        "title": _("Activity log"),
                        "icon": "manage_history",
                        "link": reverse_lazy("admin:activity_activitylog_changelist"),
                        "permission": _nav_permission("activity.view_activitylog"),
                    },
                ],
            },
        ],
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
