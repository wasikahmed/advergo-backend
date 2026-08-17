import json

from django.conf import settings
from django.contrib.auth import login as auth_login
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from .google_auth import InvalidGoogleToken, verify_google_id_token
from .models import User


@require_POST
@csrf_protect
def admin_google_login(request):
    """
    Sign-in-with-Google for the Django admin login page. Unlike the
    customer-facing API login, this never creates an account -- it only
    authenticates an *existing* staff user, matched by the email Google
    already verified. Establishes a normal Django session (same as a
    password login) without setting the 2FA-verified flag, so
    AdminTwoFactorMiddleware still routes through the usual email-OTP
    checkpoint afterwards.
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
        return JsonResponse({"detail": str(e)}, status=400)

    user = User.objects.filter(email__iexact=payload["email"], is_staff=True).first()
    if user is None:
        return JsonResponse(
            {"detail": "This Google account isn't linked to an admin account."}, status=403
        )
    if not user.is_active:
        return JsonResponse({"detail": "This admin account is inactive."}, status=403)

    # Must match settings.AUTHENTICATION_BACKENDS -- auth.get_user() on the
    # *next* request checks the stored backend path against that list and
    # silently treats the session as anonymous if it isn't there, so
    # ModelBackend (not registered) would look like a successful login here
    # and then evaporate on the very next request.
    auth_login(request, user, backend="apps.users.backends.EmailOrPhoneBackend")

    next_url = request.GET.get("next") or reverse("admin:index")
    return JsonResponse({"redirect": f"{reverse('admin-2fa-verify')}?next={next_url}"})
