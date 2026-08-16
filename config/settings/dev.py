from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "host.docker.internal", ".trycloudflare.com"]

INSTALLED_APPS += ["django_extensions"]  # noqa: F405

CORS_ALLOWED_ORIGINS = env.list(  # noqa: F405
    "CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"]
)
CORS_ALLOWED_ORIGIN_REGEXES = [r"^https://.*\.trycloudflare\.com$"]
