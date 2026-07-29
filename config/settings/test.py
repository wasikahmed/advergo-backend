import tempfile

from .base import *  # noqa: F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Tests must never depend on a live external service: always local disk here,
# regardless of whatever Cloudinary credentials happen to be set in .env. And
# never the real dev media/ dir either -- file-upload tests would otherwise
# leave artifacts there on every run.
USE_CLOUDINARY = False
STORAGES["default"] = {"BACKEND": "django.core.files.storage.FileSystemStorage"}  # noqa: F405
MEDIA_ROOT = tempfile.mkdtemp(prefix="advergo-test-media-")

# Celery tasks run synchronously and eagerly in tests -- no broker required.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
