import json

from django.conf import settings
from django.contrib.auth import login as auth_login
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.activity.models import LoginChannel
from apps.activity.services import log_login

from .admin_2fa import SESSION_VERIFIED_KEY
from .google_auth import InvalidGoogleToken, verify_google_id_token
from .models import User


@require_POST
@csrf_protect
def admin_google_login(request):
    """
    Sign-in-with-Google for the Django admin login page. Unlike the
    customer-facing API login, this never creates an account -- it only
    authenticates an *existing* staff user, matched by the email Google
    already verified. Skips the usual email-OTP 2FA checkpoint: that OTP
    would be emailed to this same address, which this Google session has
    already proven ownership of, so it isn't an independent second factor
    here the way it is after a password login -- it'd just be re-checking
    the same inbox Google already unlocked.
    """
    if not settings.GOOGLE_CLIENT_ID:
        return JsonResponse({"detail": "Google sign-in isn't configured."}, status=503)

    try:
        body = json.loads(request.body)
        id_token = body["id_token"]
    except (ValueError, KeyError):
        return JsonResponse({"detail": "Missing Google token."}, status=400)

    try:
        payload = verify_google_id_token(id_token)
    except InvalidGoogleToken as e:
        log_login(request=request, channel=LoginChannel.ADMIN_GOOGLE, success=False)
        return JsonResponse({"detail": str(e)}, status=400)

    user = User.objects.filter(email__iexact=payload["email"], is_staff=True).first()
    if user is None:
        log_login(
            request=request,
            channel=LoginChannel.ADMIN_GOOGLE,
            success=False,
            identifier=payload["email"],
        )
        return JsonResponse(
            {"detail": "This Google account isn't linked to an admin account."}, status=403
        )
    if not user.is_active:
        log_login(request=request, channel=LoginChannel.ADMIN_GOOGLE, success=False, user=user)
        return JsonResponse({"detail": "This admin account is inactive."}, status=403)

    # Must match settings.AUTHENTICATION_BACKENDS -- auth.get_user() on the
    # *next* request checks the stored backend path against that list and
    # silently treats the session as anonymous if it isn't there, so
    # ModelBackend (not registered) would look like a successful login here
    # and then evaporate on the very next request.
    auth_login(request, user, backend="apps.users.backends.EmailOrPhoneBackend")
    request.session[SESSION_VERIFIED_KEY] = True
    log_login(request=request, channel=LoginChannel.ADMIN_GOOGLE, success=True, user=user)

    next_url = request.GET.get("next") or reverse("admin:index")
    return JsonResponse({"redirect": next_url})
