from django.contrib.contenttypes.models import ContentType

from apps.core.utils import get_client_ip

from .models import ActivityLog, LoginEvent


def log_login(*, request, channel: str, success: bool, user=None, identifier: str = "") -> LoginEvent:
    return LoginEvent.objects.create(
        user=user,
        identifier=identifier or (str(user) if user else ""),
        channel=channel,
        success=success,
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
    )


def log_activity(
    *, verb: str, actor=None, request=None, target=None, description: str = "", ip_address=None
) -> ActivityLog:
    return ActivityLog.objects.create(
        actor=actor,
        verb=verb,
        content_type=ContentType.objects.get_for_model(target) if target is not None else None,
        object_id=str(target.pk) if target is not None else None,
        object_repr=str(target)[:255] if target is not None else "",
        description=description[:500],
        ip_address=ip_address or (get_client_ip(request) if request is not None else None),
    )
