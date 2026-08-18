import ipaddress

from django.contrib.contenttypes.models import ContentType
from user_agents import parse as parse_user_agent

from apps.core.utils import get_client_ip

from .models import ActivityLog, LoginEvent


def _describe_device(user_agent_string: str) -> str:
    """ "Chrome on macOS", "Safari on iPhone", ... -- parsed once at write
    time (see LoginEvent.device) rather than on every page view."""
    if not user_agent_string:
        return ""
    ua = parse_user_agent(user_agent_string)
    browser = ua.browser.family or ""
    if ua.device.family and ua.device.family not in ("Other", "Generic Smartphone"):
        platform = ua.device.family
    else:
        platform = ua.os.family or ""
    if browser and platform:
        return f"{browser} on {platform}"
    return browser or platform


def _describe_location(ip_address: str | None) -> str:
    """ "Local network" for private/loopback IPs, "City, Country" for public
    ones via MaxMind GeoLite2 (see apps.activity.geoip) -- blank if that
    database isn't installed or the IP isn't in it."""
    if not ip_address:
        return ""
    try:
        addr = ipaddress.ip_address(ip_address)
    except ValueError:
        return ""
    if addr.is_private or addr.is_loopback:
        return "Local network"

    from .geoip import resolve_location

    return resolve_location(ip_address)


def log_login(
    *, request, channel: str, success: bool, user=None, identifier: str = ""
) -> LoginEvent:
    ip_address = get_client_ip(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
    return LoginEvent.objects.create(
        user=user,
        identifier=identifier or (str(user) if user else ""),
        channel=channel,
        success=success,
        ip_address=ip_address,
        user_agent=user_agent,
        device=_describe_device(user_agent),
        location=_describe_location(ip_address),
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
