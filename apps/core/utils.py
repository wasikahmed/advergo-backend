import random
import string

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect


def generate_reference_code(prefix: str, length: int = 8) -> str:
    """Human-shareable reference code, e.g. QR-7F3K9ZAB for a quote request."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return f"{prefix}-{suffix}"


def admin_action_redirect(request: HttpRequest, url: str) -> HttpResponse:
    """
    Redirect from an Unfold admin action. Unfold's dialog forms submit via
    htmx (hx-post), which silently follows a plain 302 and tries to swap the
    resulting changelist HTML into the dialog's #dialog-form target -- since
    that id isn't there, the swap wipes the dialog blank and it never
    closes. HX-Redirect tells htmx to do a real browser navigation instead.
    Non-dialog row actions are plain <a> links (no htmx involved), so a
    normal redirect there is already correct -- this only changes behavior
    when the request actually came in via htmx.
    """
    if request.headers.get("HX-Request"):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = url
        return response
    return redirect(url)
