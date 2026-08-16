import hashlib
import secrets
import uuid
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail

OTP_LENGTH = 6
OTP_TTL_SECONDS = 10 * 60
CACHE_KEY_PREFIX = "otp"


class OTPPurpose:
    LOGIN_2FA = "login_2fa"
    PHONE_VERIFY = "phone_verify"


class OTPChannel:
    EMAIL = "email"
    SMS = "sms"


@dataclass
class VerifiedOTP:
    """What a caller gets back after a successful verify() -- deliberately
    doesn't carry the code itself, only what's needed to complete the flow."""

    identifier: str
    channel: str
    purpose: str
    user_id: str | None


def _cache_key(challenge_id: str) -> str:
    return f"{CACHE_KEY_PREFIX}:{challenge_id}"


def _hash_code(code: str) -> str:
    # SHA-256 (not a slow password hash like PBKDF2/bcrypt) is the right
    # trade-off here: the code is 6 digits with a 10-minute TTL and is
    # already rate-limited at the API layer, so the hash only needs to
    # protect against someone reading it straight out of Redis/a backup --
    # not against offline brute-forcing, which the short TTL already defeats.
    return hashlib.sha256(code.encode()).hexdigest()


def generate_otp_code() -> str:
    # secrets, not random -- this is an auth credential, not a UI shuffle.
    return "".join(secrets.choice("0123456789") for _ in range(OTP_LENGTH))


def create_otp(*, identifier: str, channel: str, purpose: str, user=None) -> tuple[str, str]:
    """Stores a new challenge in the cache with a TTL (no manual cleanup
    needed -- Redis expires it on its own). Returns (challenge_id, code);
    the caller is responsible for delivering `code` and only ever holding
    onto `challenge_id`."""
    challenge_id = str(uuid.uuid4())
    code = generate_otp_code()
    cache.set(
        _cache_key(challenge_id),
        {
            "code_hash": _hash_code(code),
            "identifier": identifier,
            "channel": channel,
            "purpose": purpose,
            "user_id": str(user.id) if user is not None else None,
        },
        timeout=OTP_TTL_SECONDS,
    )
    return challenge_id, code


def send_email_otp(identifier: str, code: str) -> None:
    send_mail(
        subject="Your Advergo verification code",
        message=(
            f"Your verification code is {code}. It expires in {OTP_TTL_SECONDS // 60} minutes. "
            "If you didn't request this, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[identifier],
    )


def create_and_send_login_2fa_otp(user) -> str:
    """Returns the challenge_id; the code itself goes straight to the user's email."""
    challenge_id, code = create_otp(
        identifier=user.email, channel=OTPChannel.EMAIL, purpose=OTPPurpose.LOGIN_2FA, user=user
    )
    send_email_otp(user.email, code)
    return challenge_id


def verify_otp(*, challenge_id: str, code: str, purpose: str) -> VerifiedOTP | None:
    """Single-use: valid challenges are deleted from the cache on both a
    successful and a failed-but-matched-purpose attempt is *not* deleted,
    so a mistyped code doesn't burn the user's only shot. Returns None on
    any mismatch/expiry/missing challenge."""
    key = _cache_key(str(challenge_id))
    data = cache.get(key)
    if data is None or data["purpose"] != purpose:
        return None
    if data["code_hash"] != _hash_code(code):
        return None

    cache.delete(key)
    return VerifiedOTP(
        identifier=data["identifier"],
        channel=data["channel"],
        purpose=data["purpose"],
        user_id=data["user_id"],
    )
