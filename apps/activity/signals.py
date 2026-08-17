from django.conf import settings
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.auth.signals import user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import LoginChannel
from .services import log_login

_VERB_BY_ACTION_FLAG = {ADDITION: "created", CHANGE: "updated", DELETION: "deleted"}


@receiver(user_login_failed)
def on_password_login_failed(sender, credentials, request=None, **kwargs):
    """
    Fires for every failed django.contrib.auth.authenticate() call --
    covers both the Django admin's own login form and the API's password
    login (SimpleJWT calls authenticate() internally too), without needing
    to instrument either by hand. Google sign-in and OTP/2FA failures don't
    go through authenticate() at all, so those are logged explicitly at
    their own call sites instead (see apps.users.views / admin_2fa).
    """
    if request is None:
        return

    identifier = credentials.get("identifier") or credentials.get("username") or ""
    channel = (
        LoginChannel.ADMIN_PASSWORD
        if request.path.startswith(f"/{settings.ADMIN_URL}")
        else LoginChannel.API_PASSWORD
    )
    log_login(request=request, channel=channel, success=False, identifier=identifier)


@receiver(post_save, sender=LogEntry)
def mirror_log_entry_to_activity(sender, instance, created, **kwargs):
    """
    Standard admin add/change/delete saves already write a LogEntry --
    mirror each one into the unified ActivityLog instead of duplicating
    that instrumentation across every ModelAdmin. Custom quick actions
    (convert to order, advance status, ...) don't create a LogEntry at
    all, so those still need their own explicit log_activity() call at
    the point they happen.
    """
    if not created:
        return

    from .models import ActivityLog

    ActivityLog.objects.create(
        actor_id=instance.user_id,
        verb=_VERB_BY_ACTION_FLAG.get(instance.action_flag, "changed"),
        content_type_id=instance.content_type_id,
        object_id=instance.object_id,
        object_repr=instance.object_repr[:255],
        description=instance.get_change_message()[:500],
    )
