import random
import string


def generate_reference_code(prefix: str, length: int = 8) -> str:
    """Human-shareable reference code, e.g. QR-7F3K9ZAB for a quote request."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return f"{prefix}-{suffix}"
