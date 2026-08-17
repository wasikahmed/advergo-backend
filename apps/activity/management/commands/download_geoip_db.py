import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

DOWNLOAD_URL = "https://download.maxmind.com/app/geoip_download"


class Command(BaseCommand):
    help = (
        "Downloads/refreshes the MaxMind GeoLite2-City database that powers "
        "the 'location' column on login events (apps.activity.LoginEvent). "
        "Needs a free MaxMind account: sign up at "
        "https://www.maxmind.com/en/geolite2/signup, generate a license key "
        "under Account > My License Keys, then set MAXMIND_LICENSE_KEY in "
        ".env. MaxMind refreshes GeoLite2 roughly twice a month -- worth "
        "re-running this periodically (e.g. a monthly cron/scheduled task) "
        "so locations don't drift stale."
    )

    def handle(self, *args, **options):
        license_key = settings.MAXMIND_LICENSE_KEY
        if not license_key:
            raise CommandError(
                "MAXMIND_LICENSE_KEY isn't set. Get a free license key from "
                "https://www.maxmind.com/en/geolite2/signup, then set it in .env."
            )

        target = Path(settings.GEOIP_PATH)
        target.parent.mkdir(parents=True, exist_ok=True)

        query = urllib.parse.urlencode(
            {"edition_id": "GeoLite2-City", "license_key": license_key, "suffix": "tar.gz"}
        )
        url = f"{DOWNLOAD_URL}?{query}"

        self.stdout.write("Downloading GeoLite2-City...")
        try:
            with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310
                archive_bytes = response.read()
        except urllib.error.HTTPError as e:
            raise CommandError(
                f"Download failed ({e.code}). Check that MAXMIND_LICENSE_KEY is still valid "
                "-- MaxMind's account page shows whether a key has been revoked."
            ) from e

        with tempfile.TemporaryDirectory() as tmp_dir:
            archive_path = Path(tmp_dir) / "geolite2-city.tar.gz"
            archive_path.write_bytes(archive_bytes)

            with tarfile.open(archive_path) as archive:
                member = next((m for m in archive.getmembers() if m.name.endswith(".mmdb")), None)
                if member is None:
                    raise CommandError("Downloaded archive didn't contain a .mmdb file.")
                extracted = archive.extractfile(member)
                target.write_bytes(extracted.read())

        # Clear the cached reader (apps.activity.geoip) so a running process
        # picks up the refreshed file without needing a restart.
        from apps.activity.geoip import _reader

        _reader.cache_clear()

        self.stdout.write(self.style.SUCCESS(f"Saved to {target}"))
