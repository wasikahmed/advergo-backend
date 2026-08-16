import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    """DRF's rate throttles (quote_submit, otp_verify, ...) share Django's
    default in-memory cache across the whole test run -- without this,
    tests that hit a throttled endpoint several times across different
    files can trip a limit that has nothing to do with what they're
    individually testing."""
    cache.clear()
    yield
    cache.clear()
