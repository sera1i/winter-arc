import json
import urllib.request
import urllib.error
from urllib.parse import urlparse
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.cache import cache


class Command(BaseCommand):
    help = "Submit canonical public Winter Arc URLs to IndexNow (Bing / Yandex / search engines)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate submission without making HTTP requests to IndexNow API.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Bypass the 24-hour submission cooldown cache.',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)

        indexnow_key = getattr(settings, 'INDEXNOW_KEY', '').strip()
        if not indexnow_key:
            self.stdout.write(
                self.style.WARNING(
                    "INDEXNOW_KEY is not configured in environment or settings. "
                    "Skipping IndexNow submission."
                )
            )
            return

        site_url = getattr(settings, 'SITE_URL', 'https://arcinwinter.up.railway.app').rstrip('/')
        parsed_url = urlparse(site_url)
        host = parsed_url.netloc or 'arcinwinter.up.railway.app'

        # Strictly canonical public indexable knowledge URLs
        public_paths = [
            '/',
            '/winter-arc/',
            '/winter-arc/rules/',
            '/winter-arc/habits/',
            '/winter-arc/challenge/',
            '/winter-arc/templates/',
            '/winter-arc/for-students/',
            '/winter-arc/for-fitness/',
            '/winter-arc/for-career/',
            '/guides/',
            '/guides/how-to-start-a-winter-arc/',
            '/guides/how-to-build-winter-arc-habits/',
            '/guides/winter-arc-daily-routine/',
            '/guides/winter-arc-goals/',
        ]
        url_list = [f"{site_url}{p}" for p in public_paths]

        cache_key = f"indexnow_last_submission_{indexnow_key[:8]}"
        last_submission = cache.get(cache_key)
        if last_submission and not force and not dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    f"IndexNow URLs were already submitted recently ({last_submission}). "
                    "Use --force to override 24h cooldown."
                )
            )
            return

        key_location = f"{site_url}/{indexnow_key}.txt"

        payload = {
            "host": host,
            "key": indexnow_key,
            "keyLocation": key_location,
            "urlList": url_list,
        }

        self.stdout.write(f"Preparing IndexNow submission for {len(url_list)} public URLs on host '{host}'...")
        self.stdout.write(f"Key verification location: {key_location}")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("[DRY-RUN] Payload prepared successfully:"))
            self.stdout.write(json.dumps(payload, indent=2))
            return

        api_endpoint = "https://api.indexnow.org/indexnow"
        data_bytes = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            api_endpoint,
            data=data_bytes,
            headers={
                'Content-Type': 'application/json; charset=utf-8',
                'User-Agent': 'WinterArc-IndexNow/1.0',
            },
            method='POST'
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                status_code = resp.getcode()
                if status_code in (200, 202):
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"IndexNow submission succeeded with HTTP {status_code}. "
                            f"{len(url_list)} URLs submitted to IndexNow."
                        )
                    )
                    cache.set(cache_key, "submitted", timeout=86400)
                else:
                    self.stdout.write(
                        self.style.WARNING(f"IndexNow responded with status: {status_code}")
                    )
        except urllib.error.HTTPError as e:
            self.stderr.write(
                self.style.ERROR(f"IndexNow submission failed with HTTP {e.code}: {e.read().decode('utf-8', 'ignore')}")
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error submitting to IndexNow: {e}"))
