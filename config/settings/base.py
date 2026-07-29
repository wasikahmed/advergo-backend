from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

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
]

LOCAL_APPS = [
    "apps.core",
    "apps.users",
    "apps.catalog",
    "apps.content",
    "apps.reviews",
    "apps.pricing",
    "apps.quotes",
    "apps.orders",
    "apps.invoices",
    "apps.wishlist",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

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

# --- Email ------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Advergo <no-reply@advergo.com>")

# --- File upload limits -----------------------------------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20 MB, matches quote-form spec
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

# --- Unfold (admin theme) ---------------------------------------------------
UNFOLD = {
    "SITE_TITLE": "Advergo Admin",
    "SITE_HEADER": "Advergo Sports & Fashion Wear Ltd.",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
