import re

from django.core import mail


def login(api_client, email, password="Str0ngPassw0rd!"):
    """Logs in via the API, with compatibility for any legacy OTP response."""
    response = api_client.post("/api/v1/auth/login/", {"identifier": email, "password": password})

    if response.data.get("twoFactorRequired"):
        code = re.search(r"code is (\d{6})", mail.outbox[-1].body).group(1)
        response = api_client.post(
            "/api/v1/auth/2fa/verify/", {"challengeId": response.data["challengeId"], "code": code}
        )

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return response
