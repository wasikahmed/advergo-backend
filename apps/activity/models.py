from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class LoginChannel(models.TextChoices):
    API_PASSWORD = "api_password", "API password"
    API_GOOGLE = "api_google", "API Google"
    ADMIN_PASSWORD = "admin_password", "Admin password"
    ADMIN_GOOGLE = "admin_google", "Admin Google"


class LoginEvent(models.Model):
    """
    One row per authentication attempt, success or failure, from every
    entry point in the app (customer/staff JWT API, Django admin session
    login, both password and Google for each). `user` is nullable because
    a failed attempt may not resolve to a real account at all (typo'd
    email, someone probing for valid accounts) -- `identifier` keeps
    whatever was typed in that case, so a pattern of failures is still
    visible even without a matching user.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="login_events",
    )
    identifier = models.CharField(max_length=255, blank=True)
    channel = models.CharField(max_length=20, choices=LoginChannel.choices)
    success = models.BooleanField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    # Parsed once at write time (from user_agent) rather than re-parsed on
    # every page view -- keeps a historical row's displayed device stable
    # even if the parsing library's rules change later, and makes it
    # filterable/searchable as plain text.
    device = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["channel", "-created_at"]),
            models.Index(fields=["success", "-created_at"]),
        ]

    def __str__(self):
        who = self.user or self.identifier or "unknown"
        return f"{who} ({self.channel}, {'ok' if self.success else 'failed'})"


class ActivityLog(models.Model):
    """
    Unified "who did what" feed. Standard admin add/change/delete saves
    are mirrored in here automatically from Django's own LogEntry (see
    signals.py) -- this only needs explicit log_activity() calls for
    things LogEntry never sees: the custom quick actions (convert to
    order, advance status, generate a document, ...) that save the object
    directly instead of going through ModelAdmin's normal save path.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    verb = models.CharField(max_length=100)
    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL)
    object_id = models.CharField(max_length=255, null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")
    object_repr = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=500, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor", "-created_at"]),
            models.Index(fields=["verb", "-created_at"]),
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.actor} {self.verb} {self.object_repr}"
