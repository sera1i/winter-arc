import json
import xml.etree.ElementTree as ET
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse

User = get_user_model()


class TechnicalSEOFoundationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='seouser', password='Password123!')

    # =========================================================================
    # 1. ROBOTS.TXT TESTS
    # =========================================================================
    def test_robots_txt_status_and_content_type(self):
        """robots.txt returns HTTP 200 with text/plain content type."""
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('text/plain'))

    def test_robots_txt_sitemap_directive(self):
        """robots.txt references the canonical sitemap.xml using SITE_URL."""
        response = self.client.get('/robots.txt')
        content = response.content.decode('utf-8')
        expected_sitemap = f"Sitemap: {settings.SITE_URL}/sitemap.xml"
        self.assertIn(expected_sitemap, content)

    def test_robots_txt_crawler_distinctions(self):
        """robots.txt explicitly configures Googlebot, Bingbot, OAI-SearchBot, and blocks GPTBot."""
        response = self.client.get('/robots.txt')
        content = response.content.decode('utf-8')

        # Check search crawlers allowed
        self.assertIn("User-agent: Googlebot", content)
        self.assertIn("User-agent: Bingbot", content)
        self.assertIn("User-agent: OAI-SearchBot", content)
        self.assertIn("Allow: /", content)
        self.assertIn("Allow: /static/", content)
        self.assertIn("Allow: /media/", content)

        # Check model-training crawler (GPTBot) is disallowed from crawling
        self.assertIn("User-agent: GPTBot", content)
        self.assertIn("Disallow: /", content)

        # Check private application routes are disallowed
        for route in [
            '/accounts/dashboard/',
            '/accounts/profile/',
            '/accounts/password-reset/',
            '/accounts/logout/',
            '/dashboard/',
            '/arcs/',
            '/goals/',
            '/tasks/',
            '/habits/',
            '/journal/',
            '/analytics/',
            '/notifications/',
            '/api/',
            '/admin/',
            '/health/',
        ]:
            self.assertIn(f"Disallow: {route}", content)

    # =========================================================================
    # 2. XML SITEMAP TESTS
    # =========================================================================
    def test_sitemap_status_and_valid_xml(self):
        """sitemap.xml returns HTTP 200 with valid sitemaps.org 0.9 XML schema."""
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('xml' in response['Content-Type'])

        content = response.content.decode('utf-8')
        # Parse XML tree
        root = ET.fromstring(content)
        self.assertEqual(root.tag, '{http://www.sitemaps.org/schemas/sitemap/0.9}urlset')

        # Check locations
        locs = [elem.text for elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
        expected_home = f"{settings.SITE_URL}/"
        self.assertIn(expected_home, locs)

    def test_sitemap_contains_no_private_routes(self):
        """sitemap.xml never includes private, authenticated, or API URLs."""
        response = self.client.get('/sitemap.xml')
        content = response.content.decode('utf-8')

        for forbidden in ['/dashboard', '/arcs', '/goals', '/tasks', '/habits', '/journal', '/analytics', '/notifications', '/api', '/admin', '/health', '/accounts']:
            self.assertNotIn(forbidden, content)

    # =========================================================================
    # 3. HOMEPAGE METADATA & CANONICAL URL TESTS
    # =========================================================================
    def test_homepage_metadata_and_title(self):
        """Homepage renders canonical meta title, description, and canonical link."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')

        # Title
        self.assertIn('<title>Winter Arc — 90-Day Self-Improvement &amp; Discipline Tracker</title>', html)

        # Meta description
        expected_desc = "Build your Winter Arc with structured goals, habits, tasks, journaling, and progress tracking. Create your system, keep the season, and build lasting discipline."
        self.assertIn(f'name="description" content="{expected_desc}"', html)

        # Canonical URL using SITE_URL
        expected_canonical = f'<link rel="canonical" href="{settings.SITE_URL}/">'
        self.assertIn(expected_canonical, html)

        # Robots index, follow
        self.assertIn('name="robots" content="index, follow"', html)

    def test_homepage_open_graph_metadata(self):
        """Homepage renders Open Graph tags with absolute URLs and factual branding."""
        from django.templatetags.static import static
        response = self.client.get('/')
        html = response.content.decode('utf-8')

        self.assertIn('<meta property="og:site_name" content="Winter Arc">', html)
        self.assertIn('property="og:title" content="Winter Arc — 90-Day Self-Improvement &amp; Discipline Tracker"', html)
        self.assertIn('property="og:type" content="website"', html)
        self.assertIn(f'property="og:url" content="{settings.SITE_URL}/"', html)
        expected_og_image = f"{settings.SITE_URL}{static('images/og-winter-arc.jpg')}"
        self.assertIn(f'property="og:image" content="{expected_og_image}"', html)
        self.assertIn('property="og:image:width" content="1200"', html)
        self.assertIn('property="og:image:height" content="630"', html)

    def test_homepage_twitter_metadata(self):
        """Homepage renders Twitter/X large summary card metadata."""
        from django.templatetags.static import static
        response = self.client.get('/')
        html = response.content.decode('utf-8')

        self.assertIn('<meta name="twitter:card" content="summary_large_image">', html)
        self.assertIn('name="twitter:title" content="Winter Arc — 90-Day Self-Improvement &amp; Discipline Tracker"', html)
        expected_og_image = f"{settings.SITE_URL}{static('images/og-winter-arc.jpg')}"
        self.assertIn(f'name="twitter:image" content="{expected_og_image}"', html)

    def test_homepage_icons_and_manifest(self):
        """Homepage links to favicon.svg, apple-touch-icon.png, site.webmanifest, and theme-color."""
        from django.templatetags.static import static
        response = self.client.get('/')
        html = response.content.decode('utf-8')

        expected_favicon = static('favicon.svg')
        expected_apple = static('apple-touch-icon.png')
        expected_manifest = static('site.webmanifest')

        self.assertIn(f'href="{expected_favicon}"', html)
        self.assertIn(f'href="{expected_apple}"', html)
        self.assertIn(f'href="{expected_manifest}"', html)
        self.assertIn('name="theme-color" content="#0B0D12"', html)

    # =========================================================================
    # 4. JSON-LD STRUCTURED DATA TESTS
    # =========================================================================
    def test_homepage_json_ld_schema(self):
        """Homepage provides valid, schema-compliant JSON-LD with WebSite, Organization, and SoftwareApplication."""
        response = self.client.get('/')
        html = response.content.decode('utf-8')

        self.assertIn('type="application/ld+json"', html)
        # Extract script content
        start = html.find('<script type="application/ld+json">') + len('<script type="application/ld+json">')
        end = html.find('</script>', start)
        json_text = html[start:end].strip()

        data = json.loads(json_text)
        self.assertEqual(data.get('@context'), 'https://schema.org')
        graph = data.get('@graph', [])
        types = {item.get('@type'): item for item in graph}

        # 1. WebSite
        self.assertIn('WebSite', types)
        self.assertEqual(types['WebSite']['name'], 'Winter Arc')
        self.assertEqual(types['WebSite']['url'], f"{settings.SITE_URL}/")

        # 2. Organization
        self.assertIn('Organization', types)
        self.assertEqual(types['Organization']['name'], 'Winter Arc')
        self.assertEqual(types['Organization']['url'], f"{settings.SITE_URL}/")

        # 3. SoftwareApplication
        self.assertIn('SoftwareApplication', types)
        self.assertEqual(types['SoftwareApplication']['name'], 'Winter Arc')
        self.assertEqual(types['SoftwareApplication']['applicationCategory'], 'ProductivityApplication')
        self.assertEqual(types['SoftwareApplication']['operatingSystem'], 'Web')
        self.assertEqual(types['SoftwareApplication']['url'], f"{settings.SITE_URL}/")

        # Ensure no fabricated ratings or prices
        self.assertNotIn('aggregateRating', types['SoftwareApplication'])
        self.assertNotIn('offers', types['SoftwareApplication'])

    # =========================================================================
    # 5. 404 PAGE TESTS
    # =========================================================================
    def test_unknown_url_returns_404_with_noindex(self):
        """Nonexistent URL returns HTTP 404 with noindex directive and return link."""
        response = self.client.get('/completely-nonexistent-path-for-seo-test-404/')
        self.assertEqual(response.status_code, 404)
        html = response.content.decode('utf-8')

        self.assertIn('404', html)
        self.assertIn('name="robots" content="noindex, nofollow"', html)
        self.assertIn('Return to Sanctuary', html)
        self.assertIn('href="/"', html)

    # =========================================================================
    # 6. PRIVATE PAGE INDEX CONTROL TESTS
    # =========================================================================
    def test_private_authenticated_pages_have_noindex(self):
        """Authenticated application pages render noindex, nofollow directive in base.html."""
        self.client.force_login(self.user)
        for url in ['/accounts/dashboard/', '/arcs/', '/tasks/', '/habits/', '/journal/', '/analytics/', '/accounts/profile/']:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200, f"Failed loading {url}")
                html = response.content.decode('utf-8')
                self.assertIn('name="robots" content="noindex, nofollow"', html, f"noindex missing on {url}")
                # Ensure private pages do NOT have a canonical tag pointing to landing page
                self.assertNotIn('<link rel="canonical" href="https://arcinwinter.up.railway.app/">', html)
                self.assertNotIn('<link rel="canonical" href="http://127.0.0.1:8000/">', html)

    # =========================================================================
    # 7. SITE_URL NORMALIZATION & CONTEXT PROCESSOR TESTS
    # =========================================================================
    def test_site_url_trailing_slash_normalization(self):
        """SITE_URL is normalized without trailing slash."""
        self.assertFalse(settings.SITE_URL.endswith('/'))

    @override_settings(SITE_URL='https://custom.domain.com')
    def test_custom_site_url_override(self):
        """Custom SITE_URL is normalized and passed to templates."""
        from core.context_processors import seo_context
        from django.test import RequestFactory
        req = RequestFactory().get('/')
        ctx = seo_context(req)
        self.assertEqual(ctx['SITE_URL'], 'https://custom.domain.com')
        self.assertFalse(ctx['SITE_URL'].endswith('/'))
