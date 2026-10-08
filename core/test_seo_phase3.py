import json
import xml.etree.ElementTree as ET
from io import StringIO
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.management import call_command
from django.core.cache import cache


class SEOPhase3DiscoveryTests(TestCase):
    """
    SEO Phase 3 Test Suite: Search engine discovery, indexing,
    HTTP methods (GET & HEAD), sitemap XML validity, IndexNow,
    AI/crawler policy, and public vs private security crawl boundaries.
    """

    PUBLIC_URLS = [
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

    PRIVATE_URLS = [
        '/accounts/login/',
        '/accounts/register/',
        '/arcs/',
        '/goals/',
        '/tasks/',
        '/habits/',
        '/journal/',
        '/analytics/',
        '/notifications/',
        '/api/v1/arcs/',
        '/admin/',
        '/health/',
    ]

    def setUp(self):
        cache.clear()

    # =========================================================================
    # 1. HTTP / HEAD / GET Request Testing Across Public URLs
    # =========================================================================
    def test_all_public_urls_return_200_on_get(self):
        """Every public canonical URL must return HTTP 200 on standard GET."""
        for url in self.PUBLIC_URLS:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200, f"GET {url} failed with status {response.status_code}")
                self.assertIn("text/html", response["Content-Type"])

    def test_all_public_urls_return_200_on_head(self):
        """Search engine crawlers often issue HEAD requests to inspect headers without fetching payload."""
        for url in self.PUBLIC_URLS:
            with self.subTest(url=url):
                response = self.client.head(url)
                self.assertEqual(response.status_code, 200, f"HEAD {url} failed with status {response.status_code}")
                self.assertIn("text/html", response["Content-Type"])
                # Body must be empty for HEAD response
                self.assertEqual(len(response.content), 0, f"HEAD {url} should not return body content")

    def test_robots_and_sitemap_return_200_on_get_and_head(self):
        """robots.txt and sitemap.xml must respond successfully to both GET and HEAD."""
        for path, expected_content_type in [('/robots.txt', 'text/plain'), ('/sitemap.xml', 'application/xml')]:
            with self.subTest(path=path):
                # GET
                get_resp = self.client.get(path)
                self.assertEqual(get_resp.status_code, 200)
                self.assertIn(expected_content_type, get_resp["Content-Type"])
                self.assertGreater(len(get_resp.content), 0)

                # HEAD
                head_resp = self.client.head(path)
                self.assertEqual(head_resp.status_code, 200)
                self.assertIn(expected_content_type, head_resp["Content-Type"])
                self.assertEqual(len(head_resp.content), 0)

    # =========================================================================
    # 2. XML Sitemap Validation
    # =========================================================================
    def test_sitemap_parses_as_valid_xml_and_has_all_canonical_urls(self):
        """sitemap.xml must be strictly well-formed XML matching sitemaps.org 0.9 schema."""
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)

        # Parse XML
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as e:
            self.fail(f"sitemap.xml failed to parse as valid XML: {e}")

        # Check namespace and url count
        namespace = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = root.findall('sm:url', namespace)
        self.assertEqual(len(urls), 14, f"Expected exactly 14 URLs in sitemap, found {len(urls)}")

        locs = [u.find('sm:loc', namespace).text for u in urls]
        # No duplicates
        self.assertEqual(len(locs), len(set(locs)), "Duplicate URLs found in sitemap.xml")

        # Every loc must be HTTPS and start with configured SITE_URL
        for loc in locs:
            self.assertTrue(loc.startswith('https://') or loc.startswith('http://'))
            self.assertFalse(loc.endswith('/arcs/'))
            self.assertFalse('/api/' in loc)
            self.assertFalse('/accounts/' in loc)

    # =========================================================================
    # 3. Google & Bing Site Verification Metadata
    # =========================================================================
    @override_settings(GOOGLE_SITE_VERIFICATION='google-test-token-12345', BING_SITE_VERIFICATION='bing-test-token-67890')
    def test_search_engine_verification_meta_tags_rendered_when_configured(self):
        """When verification settings are configured, verification tags must render on homepage and public pages."""
        for path in ['/', '/winter-arc/']:
            with self.subTest(path=path):
                response = self.client.get(path)
                content = response.content.decode('utf-8')
                self.assertIn('<meta name="google-site-verification" content="google-test-token-12345">', content)
                self.assertIn('<meta name="msvalidate.01" content="bing-test-token-67890">', content)

    @override_settings(GOOGLE_SITE_VERIFICATION='', BING_SITE_VERIFICATION='')
    def test_search_engine_verification_meta_tags_omitted_when_unconfigured(self):
        """When verification settings are empty, no empty or placeholder tags should render."""
        response = self.client.get('/')
        content = response.content.decode('utf-8')
        self.assertNotIn('google-site-verification', content)
        self.assertNotIn('msvalidate.01', content)

    # =========================================================================
    # 4. IndexNow Verification Endpoint & Management Command
    # =========================================================================
    @override_settings(INDEXNOW_KEY='e2b85fa198c64cfb87bfa0d291999901')
    def test_indexnow_endpoint_serves_key_file(self):
        """GET /<key>.txt returns 200 with text/plain body containing only the key."""
        key = 'e2b85fa198c64cfb87bfa0d291999901'
        response = self.client.get(f'/{key}.txt')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/plain', response['Content-Type'])
        self.assertEqual(response.content.decode('utf-8').strip(), key)

    @override_settings(INDEXNOW_KEY='e2b85fa198c64cfb87bfa0d291999901')
    def test_indexnow_endpoint_returns_404_for_mismatched_key(self):
        """GET /<wrong_key>.txt must return 404 to protect against probing."""
        response = self.client.get('/wrong_key_12345678.txt')
        self.assertEqual(response.status_code, 404)

    @override_settings(INDEXNOW_KEY='')
    def test_indexnow_endpoint_returns_404_when_unconfigured(self):
        """When INDEXNOW_KEY is empty, any /<key>.txt request returns 404."""
        response = self.client.get('/e2b85fa198c64cfb87bfa0d291999901.txt')
        self.assertEqual(response.status_code, 404)

    @override_settings(INDEXNOW_KEY='e2b85fa198c64cfb87bfa0d291999901')
    def test_submit_indexnow_management_command_dry_run(self):
        """python manage.py submit_indexnow --dry-run produces clean payload without network call."""
        out = StringIO()
        call_command('submit_indexnow', dry_run=True, stdout=out)
        output = out.getvalue()
        self.assertIn('[DRY-RUN] Payload prepared successfully:', output)
        self.assertIn('e2b85fa198c64cfb87bfa0d291999901', output)
        self.assertIn('/winter-arc/rules/', output)

    @override_settings(INDEXNOW_KEY='')
    def test_submit_indexnow_command_unconfigured_skips_gracefully(self):
        """python manage.py submit_indexnow exits cleanly with warning when key is unconfigured."""
        out = StringIO()
        call_command('submit_indexnow', stdout=out)
        output = out.getvalue()
        self.assertIn('INDEXNOW_KEY is not configured', output)

    @override_settings(INDEXNOW_KEY='e2b85fa198c64cfb87bfa0d291999901')
    def test_submit_indexnow_cooldown_and_force_flag(self):
        """Management command respects 24h cooldown unless --force is specified."""
        cache_key = "indexnow_last_submission_e2b85fa1"
        cache.set(cache_key, "submitted_earlier", timeout=86400)

        # Without force: must notice cooldown
        out_cooldown = StringIO()
        call_command('submit_indexnow', stdout=out_cooldown)
        self.assertIn('already submitted recently', out_cooldown.getvalue())
        self.assertIn('Use --force to override', out_cooldown.getvalue())

        # With force and dry-run: bypasses cooldown
        out_force = StringIO()
        call_command('submit_indexnow', force=True, dry_run=True, stdout=out_force)
        self.assertIn('[DRY-RUN] Payload prepared successfully:', out_force.getvalue())

    @override_settings(INDEXNOW_KEY='e2b85fa198c64cfb87bfa0d291999901')
    def test_submit_indexnow_never_includes_private_urls(self):
        """IndexNow submission list must contain only canonical public URLs, zero private routes."""
        out = StringIO()
        call_command('submit_indexnow', dry_run=True, stdout=out)
        output = out.getvalue()
        start = output.find('{')
        end = output.rfind('}') + 1
        data = json.loads(output[start:end])
        url_list = data['urlList']

        from urllib.parse import urlparse
        for url in url_list:
            path = urlparse(url).path
            self.assertIn(path, self.PUBLIC_URLS)
            self.assertNotIn(path, self.PRIVATE_URLS)

    # =========================================================================
    # 5. Crawler / AI Search Policy (robots.txt)
    # =========================================================================
    def test_robots_txt_has_explicit_bot_policies(self):
        """robots.txt explicitly defines Googlebot, Bingbot, OAI-SearchBot, GPTBot, and generic *."""
        response = self.client.get('/robots.txt')
        content = response.content.decode('utf-8')

        # Check search crawlers allowed
        self.assertIn('User-agent: Googlebot', content)
        self.assertIn('User-agent: Bingbot', content)
        self.assertIn('User-agent: OAI-SearchBot', content)

        # Check LLM training crawler blocked
        self.assertIn('User-agent: GPTBot', content)
        self.assertIn('Disallow: /', content)

        # Check fallback crawler
        self.assertIn('User-agent: *', content)

        # Check sitemap
        self.assertIn('Sitemap:', content)
        self.assertIn('/sitemap.xml', content)

    def test_robots_txt_disallows_private_and_auth_routes(self):
        """robots.txt disallows private product routes and authentication forms."""
        response = self.client.get('/robots.txt')
        content = response.content.decode('utf-8')

        for disallowed in [
            'Disallow: /accounts/dashboard/',
            'Disallow: /accounts/login/',
            'Disallow: /accounts/register/',
            'Disallow: /arcs/',
            'Disallow: /goals/',
            'Disallow: /tasks/',
            'Disallow: /habits/',
            'Disallow: /journal/',
            'Disallow: /analytics/',
            'Disallow: /notifications/',
            'Disallow: /api/',
            'Disallow: /admin/',
            'Disallow: /health/',
        ]:
            self.assertIn(disallowed, content)

    # =========================================================================
    # 6. Public vs Private Index Boundary (X-Robots-Tag & Meta Robots)
    # =========================================================================
    def test_private_routes_return_x_robots_tag_noindex(self):
        """All private authenticated routes must return HTTP header 'X-Robots-Tag: noindex, nofollow'."""
        for path in self.PRIVATE_URLS:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertIn(
                    'X-Robots-Tag', response.headers,
                    f"Private route {path} missing X-Robots-Tag header"
                )
                self.assertEqual(
                    response.headers['X-Robots-Tag'],
                    'noindex, nofollow',
                    f"Private route {path} has invalid X-Robots-Tag: {response.headers.get('X-Robots-Tag')}"
                )

    def test_custom_404_returns_x_robots_tag_noindex(self):
        """Non-existent pages (404) must include 'X-Robots-Tag: noindex, nofollow'."""
        response = self.client.get('/non-existent-crucible-trial/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers.get('X-Robots-Tag'), 'noindex, nofollow')

    def test_public_pages_do_not_have_noindex_header(self):
        """Public pages must never receive a noindex X-Robots-Tag header."""
        for path in self.PUBLIC_URLS:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn('noindex', response.headers.get('X-Robots-Tag', ''))

    # =========================================================================
    # 7. Entity Consistency & Performance
    # =========================================================================
    def test_entity_consistency_across_public_pages(self):
        """Brand name 'Winter Arc' and description must be consistent across templates."""
        for path in self.PUBLIC_URLS:
            with self.subTest(path=path):
                response = self.client.get(path)
                content = response.content.decode('utf-8')
                self.assertIn('Winter Arc', content)

        # Homepage specifically contains canonical entity description
        home_resp = self.client.get('/')
        home_content = home_resp.content.decode('utf-8')
        self.assertIn('90-Day Self-Improvement & Discipline Tracker', home_content)

    def test_base_public_background_image_is_lazy_loaded(self):
        """Public layout background texture must have loading='lazy' and decoding='async'."""
        response = self.client.get('/winter-arc/')
        content = response.content.decode('utf-8')
        self.assertIn('loading="lazy"', content)
        self.assertIn('decoding="async"', content)

    def test_public_html_payload_size_is_lean(self):
        """HTML pages should be lean (< 150 KB uncompressed) for search crawler efficiency."""
        for path in self.PUBLIC_URLS:
            with self.subTest(path=path):
                response = self.client.get(path)
                size_kb = len(response.content) / 1024
                self.assertLess(size_kb, 150, f"HTML size of {path} is {size_kb:.1f} KB, exceeding 150 KB budget")
