from django.conf import settings
from django.shortcuts import redirect
from django.urls import Resolver404, resolve

from .admin_2fa import SESSION_VERIFIED_KEY

# URL names reachable without having passed the 2FA checkpoint yet -- the
# login page itself, the checkpoint page, logout, and the classic Django
# password-reset flow (a locked-out admin needs to reach these to get in).
EXEMPT_URL_NAMES = {
    "admin:login",
    "admin:logout",
    "admin-2fa-verify",
    "admin_password_reset",
    "password_reset_done",
    "password_reset_confirm",
    "password_reset_complete",
}


class AdminTwoFactorMiddleware:
    """
    Gates the Django admin site (session-based login) behind the same
    email-OTP step the API's JWT login enforces for staff. Doesn't touch the
    DRF API, which has its own 2FA challenge in apps.users.views.LoginView --
    this only applies to requests under settings.ADMIN_URL.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_prefix = f"/{settings.ADMIN_URL}"

    def __call__(self, request):
        if self._requires_verification(request):
            next_url = request.path
            return redirect(f"/admin-2fa/verify/?next={next_url}")
        return self.get_response(request)

    def _requires_verification(self, request):
        if not request.path.startswith(self.admin_prefix):
            return False

        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated or not user.is_staff:
            return False

        if request.session.get(SESSION_VERIFIED_KEY):
            return False

        try:
            match = resolve(request.path)
        except Resolver404:
            return True

        full_name = f"{match.namespace}:{match.url_name}" if match.namespace else match.url_name
        return full_name not in EXEMPT_URL_NAMES and match.url_name not in EXEMPT_URL_NAMES
