import re

from django.core import mail


def login(api_client, email, password="Str0ngPassw0rd!"):
    """Logs in via the API, transparently completing the email-OTP 2FA step
    for staff accounts. The code itself is only ever stored as a hash, so
    it's read out of the sent email body (tests use the locmem backend)
    rather than queried back from storage."""
    response = api_client.post("/api/v1/auth/login/", {"identifier": email, "password": password})

    if response.data.get("twoFactorRequired"):
        code = re.search(r"code is (\d{6})", mail.outbox[-1].body).group(1)
        response = api_client.post(
            "/api/v1/auth/2fa/verify/", {"challengeId": response.data["challengeId"], "code": code}
        )

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return response
