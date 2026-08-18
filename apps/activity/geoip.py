from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def _reader():
    """
    Lazily opens the GeoLite2 database once and keeps it open for the
    process's lifetime (it's just a memory-mapped file, cheap to hold
    open, expensive to reopen on every login). Returns None if the file
    hasn't been downloaded yet -- see the download_geoip_db management
    command -- so callers degrade to "no location" instead of erroring.
    """
    import geoip2.database

    try:
        return geoip2.database.Reader(settings.GEOIP_PATH)
    except (FileNotFoundError, ValueError):
        return None


def resolve_location(ip_address: str) -> str:
    """ "City, Country", best-effort. Empty string if the database isn't
    installed, the IP isn't in it (common for hosting-provider ranges,
    always true for private IPs), or anything else goes wrong -- this is
    a nice-to-have display field, never worth failing a login over."""
    reader = _reader()
    if reader is None:
        return ""

    import geoip2.errors

    try:
        response = reader.city(ip_address)
    except (geoip2.errors.AddressNotFoundError, ValueError):
        return ""

    # Some IPs (anycast/CDN ranges are the common case -- e.g. 1.1.1.1) have
    # no `country` (where it's actually used) but do have
    # `registered_country` (where the block was allocated) -- fall back
    # rather than silently dropping the country for those.
    country = response.country.name or response.registered_country.name
    parts = [response.city.name, country]
    return ", ".join(p for p in parts if p)
