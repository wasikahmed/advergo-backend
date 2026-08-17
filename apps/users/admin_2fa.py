from django.contrib import admin, messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.activity.models import LoginChannel
from apps.activity.services import log_login

from .otp import OTPPurpose, create_and_send_login_2fa_otp, verify_otp

SESSION_CHALLENGE_KEY = "admin_2fa_challenge_id"
SESSION_VERIFIED_KEY = "admin_2fa_verified"


@login_required
def verify(request):
    """
    Standalone email-OTP checkpoint sitting between Django's normal admin
    session login and the rest of the admin site (enforced by
    AdminTwoFactorMiddleware). Session-based, not the API's JWT 2FA flow --
    both share the same OTP cache mechanism/purpose, just issued and
    consumed differently.
    """
    next_url = request.GET.get("next") or reverse("admin:index")

    if not request.user.is_staff:
        return redirect(next_url)

    if request.session.get(SESSION_VERIFIED_KEY):
        return redirect(next_url)

    challenge_id = request.session.get(SESSION_CHALLENGE_KEY)

    if request.method == "POST":
        if "resend" in request.POST:
            challenge_id = create_and_send_login_2fa_otp(request.user)
            request.session[SESSION_CHALLENGE_KEY] = challenge_id
            messages.success(request, "A new code has been sent.")
            return redirect(f"{reverse('admin-2fa-verify')}?next={next_url}")

        code = request.POST.get("code", "")
        otp = (
            verify_otp(challenge_id=challenge_id, code=code, purpose=OTPPurpose.LOGIN_2FA)
            if challenge_id
            else None
        )
        if otp is None or otp.user_id != str(request.user.id):
            log_login(
                request=request,
                channel=LoginChannel.ADMIN_PASSWORD,
                success=False,
                user=request.user,
            )
            messages.error(request, "Invalid or expired code.")
        else:
            request.session[SESSION_VERIFIED_KEY] = True
            request.session.pop(SESSION_CHALLENGE_KEY, None)
            log_login(
                request=request,
                channel=LoginChannel.ADMIN_PASSWORD,
                success=True,
                user=request.user,
            )
            return redirect(next_url)
    elif not challenge_id:
        challenge_id = create_and_send_login_2fa_otp(request.user)
        request.session[SESSION_CHALLENGE_KEY] = challenge_id

    context = {"next": next_url, "title": "Verify it's you", **admin.site.each_context(request)}
    return render(request, "admin_2fa_verify.html", context)
