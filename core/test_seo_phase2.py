import json
import xml.etree.ElementTree as ET
from django.test import TestCase
from django.conf import settings
from django.urls import reverse


class TechnicalSEOPhase2Tests(TestCase):
    """
    Automated test suite for Winter Arc SEO Phase 2:
    Public Content, Topical Authority, AEO/GEO, and Knowledge Ecosystem.
    """

    PUBLIC_ROUTES = [
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

    def test_all_phase2_routes_return_200(self):
        """Every Phase 2 public route returns HTTP 200."""
        for path in self.PUBLIC_ROUTES:
            with self.subTest(path=path):
                resp = self.client.get(path)
                self.assertEqual(resp.status_code, 200, f"Path {path} returned status {resp.status_code}")

    def test_canonical_urls_and_robots_index_follow(self):
        """Every public route defines its exact self-referencing canonical URL and 'index, follow' robots tag."""
        for path in self.PUBLIC_ROUTES:
            with self.subTest(path=path):
                resp = self.client.get(path)
                html = resp.content.decode('utf-8')

                expected_canonical = f'<link rel="canonical" href="{settings.SITE_URL}{path}">'
                self.assertIn(expected_canonical, html, f"Canonical tag missing or incorrect on {path}")
                self.assertIn('<meta name="robots" content="index, follow">', html, f"index, follow missing on {path}")

    def test_titles_and_descriptions_are_unique_and_substantial(self):
        """Every Phase 2 route has a unique title and substantial meta description."""
        titles = set()
        descriptions = set()

        for path in self.PUBLIC_ROUTES:
            resp = self.client.get(path)
            html = resp.content.decode('utf-8')

            # Extract title
            self.assertIn('<title>', html, f"Title tag missing on {path}")
            title_chunk = html.split('<title>')[1].split('</title>')[0].strip()
            self.assertTrue(len(title_chunk) > 15, f"Title too short on {path}")
            self.assertNotIn(title_chunk, titles, f"Duplicate title detected for {path}: {title_chunk}")
            titles.add(title_chunk)

            # Extract meta description
            self.assertIn('name="description" content="', html, f"Meta description missing on {path}")
            desc_chunk = html.split('name="description" content="')[1].split('"')[0].strip()
            self.assertTrue(len(desc_chunk) > 40, f"Meta description too short on {path}")
            self.assertNotIn(desc_chunk, descriptions, f"Duplicate description detected for {path}")
            descriptions.add(desc_chunk)

    def test_structured_data_json_ld_validity(self):
        """Every public route embeds valid, well-formed Schema.org JSON-LD."""
        for path in self.PUBLIC_ROUTES:
            with self.subTest(path=path):
                resp = self.client.get(path)
                html = resp.content.decode('utf-8')

                self.assertIn('<script type="application/ld+json">', html, f"JSON-LD missing on {path}")
                json_raw = html.split('<script type="application/ld+json">')[1].split('</script>')[0].strip()
                data = json.loads(json_raw)

                self.assertEqual(data.get('@context'), 'https://schema.org', f"Incorrect @context on {path}")
                graph = data.get('@graph', [])
                self.assertTrue(len(graph) >= 1, f"Empty @graph on {path}")

                types = [item.get('@type') for item in graph]
                self.assertIn('BreadcrumbList', types, f"BreadcrumbList missing in JSON-LD on {path}")

                # Ensure zero fabricated reviews/ratings/prices
                for item in graph:
                    item_type = item.get('@type', '')
                    self.assertNotEqual(item_type, 'AggregateRating', f"Fabricated ratings found on {path}")
                    self.assertNotEqual(item_type, 'Review', f"Fabricated reviews found on {path}")
                    self.assertNotEqual(item_type, 'Offer', f"Fabricated offers found on {path}")

    def test_sitemap_contains_all_14_canonical_urls(self):
        """The XML sitemap lists the homepage plus all 13 Phase 2 public pages, and zero private URLs."""
        resp = self.client.get('/sitemap.xml')
        self.assertEqual(resp.status_code, 200)
        xml_content = resp.content.decode('utf-8')
        root = ET.fromstring(xml_content)

        locs = [el.text for el in root.iter() if el.tag.endswith('loc')]

        # Check homepage
        self.assertIn(f"{settings.SITE_URL}/", locs, "Homepage missing in sitemap.xml")

        # Check all 13 public routes
        for path in self.PUBLIC_ROUTES:
            expected_loc = f"{settings.SITE_URL}{path}"
            self.assertIn(expected_loc, locs, f"Route {expected_loc} missing in sitemap.xml")

        # Check total count is exactly 14 public pages
        self.assertEqual(len(locs), 14, f"Expected 14 public URLs in sitemap, got {len(locs)}: {locs}")

        # Check zero private routes
        forbidden_prefixes = ['/accounts/', '/arcs/', '/goals/', '/tasks/', '/habits/', '/journal/', '/analytics/', '/api/', '/admin/']
        for forbidden in forbidden_prefixes:
            for loc in locs:
                if loc != f"{settings.SITE_URL}/":
                    path_part = loc.replace(settings.SITE_URL, '')
                    self.assertFalse(path_part.startswith(forbidden), f"Private URL leaked into sitemap: {loc}")

    def test_robots_txt_allows_public_knowledge_routes(self):
        """robots.txt explicitly allows public routes and does not block /winter-arc/ or /guides/."""
        resp = self.client.get('/robots.txt')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')

        self.assertIn("Allow: /", content)
        self.assertNotIn("Disallow: /winter-arc/", content)
        self.assertNotIn("Disallow: /guides/", content)

    def test_answer_first_h1_and_summary_box(self):
        """Every public page has a single H1 and an immediate Direct Answer / Overview block."""
        for path in self.PUBLIC_ROUTES:
            with self.subTest(path=path):
                resp = self.client.get(path)
                html = resp.content.decode('utf-8')

                # Exactly one H1
                self.assertEqual(html.count('<h1'), 1, f"Expected exactly 1 <h1> tag on {path}")

                # Answer-First callout box present
                self.assertTrue(
                    'Direct Definition' in html or 'Direct Answer' in html or 'Direct Overview' in html,
                    f"Direct Answer / AEO block missing on {path}"
                )

    def test_preset_blueprint_ctas_resolve(self):
        """Template blueprint review CTAs resolve cleanly."""
        resp = self.client.get('/winter-arc/templates/')
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode('utf-8')

        # Check that preset review links are embedded
        for preset_key in ['classic', 'student', 'fitness', 'monk_mode', 'mind_body', 'career', 'custom']:
            expected_href = reverse('arcs:preset_review', kwargs={'key': preset_key})
            self.assertIn(expected_href, html, f"Preset link {expected_href} missing on templates page")

    def test_no_stale_preset_names_or_unsupported_claims(self):
        """Rendered HTML on all public routes contains zero stale preset names or unsupported claims."""
        stale_terms = [
            "Standard Foundation",
            "Minimalist Reset",
            "Academic Overhaul",
            "Athletic Conditioning",
            "All 5 Core Presets",
            "5 Core Presets",
            "five core presets",
            "official Winter Arc rules",
            "thousands of users",
            "why millions choose",
            "award-winning",
            "trusted by",
        ]
        for path in self.PUBLIC_ROUTES:
            resp = self.client.get(path)
            html = resp.content.decode('utf-8')
            for term in stale_terms:
                self.assertNotIn(term.lower(), html.lower(), f"Stale or unsupported term '{term}' found on {path}")

    def test_fitness_page_contains_medical_disclaimer(self):
        """The /winter-arc/for-fitness/ page includes an explicit health disclaimer."""
        resp = self.client.get('/winter-arc/for-fitness/')
        html = resp.content.decode('utf-8')
        self.assertIn("does not constitute medical", html)

    def test_templates_page_displays_all_six_predefined_presets_plus_custom(self):
        """The /winter-arc/templates/ page displays all 6 canonical predefined presets + Custom Arc."""
        resp = self.client.get('/winter-arc/templates/')
        html = resp.content.decode('utf-8')
        canonical_presets = [
            "Classic Winter Arc",
            "Student Lock-In",
            "Fitness Arc",
            "Monk Mode",
            "Mind + Body",
            "Career Lock-In",
            "Custom Arc",
        ]
        for name in canonical_presets:
            self.assertIn(name, html, f"Canonical preset '{name}' missing on templates page")
