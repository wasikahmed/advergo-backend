from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token


class InvalidGoogleToken(Exception):
    pass


def verify_google_id_token(token: str) -> dict:
    """Verifies a Google ID token and returns its payload, requiring a
    verified email -- shared by the customer-facing API login and the admin
    login button so both trust Google the same way."""
    try:
        payload = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        raise InvalidGoogleToken("Invalid Google token.") from e

    if not payload.get("email") or not payload.get("email_verified"):
        raise InvalidGoogleToken("Google account has no verified email.")

    return payload
