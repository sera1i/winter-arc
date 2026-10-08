import os
import sys
import json
import time
import xml.etree.ElementTree as ET
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'winter_arc.settings')
django.setup()

from django.test import Client
from django.conf import settings

client = Client()

PUBLIC_PATHS = [
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

PRIVATE_PATHS = [
    '/accounts/login/',
    '/accounts/register/',
    '/accounts/dashboard/',
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
    '/non-existent-page-test-404/',
]

print("=" * 80)
print("SEO PHASE 3 COMPREHENSIVE PRODUCTION AUDIT")
print("=" * 80)

# 1. Performance, GET & HEAD on Public Pages
print("\n[AUDIT 1] Public URLs: GET, HEAD, Status, Latency & Payload Size")
for path in PUBLIC_PATHS:
    t0 = time.time()
    get_resp = client.get(path)
    t_get = (time.time() - t0) * 1000

    t0 = time.time()
    head_resp = client.head(path)
    t_head = (time.time() - t0) * 1000

    size_kb = len(get_resp.content) / 1024
    content = get_resp.content.decode('utf-8')
    has_meta_robots = 'name="robots" content="index, follow"' in content
    noindex_header = 'noindex' in get_resp.headers.get('X-Robots-Tag', '')

    print(f"  {path:<35} GET: {get_resp.status_code} ({t_get:.1f}ms) | HEAD: {head_resp.status_code} ({t_head:.1f}ms) | Size: {size_kb:.1f}KB | Robots: {'OK' if has_meta_robots and not noindex_header else 'FAIL'}")
    assert get_resp.status_code == 200
    assert head_resp.status_code == 200
    assert not noindex_header
    assert has_meta_robots

# 2. robots.txt and sitemap.xml
print("\n[AUDIT 2] robots.txt & sitemap.xml Direct Validation")
robots_resp = client.get('/robots.txt')
print(f"  /robots.txt: Status {robots_resp.status_code}, Content-Type: {robots_resp['Content-Type']}, Size: {len(robots_resp.content)} bytes")
assert robots_resp.status_code == 200
assert 'text/plain' in robots_resp['Content-Type']
assert 'User-agent: Googlebot' in robots_resp.content.decode('utf-8')
assert 'User-agent: Bingbot' in robots_resp.content.decode('utf-8')
assert 'User-agent: OAI-SearchBot' in robots_resp.content.decode('utf-8')
assert 'User-agent: GPTBot\nDisallow: /' in robots_resp.content.decode('utf-8')

sitemap_resp = client.get('/sitemap.xml')
print(f"  /sitemap.xml: Status {sitemap_resp.status_code}, Content-Type: {sitemap_resp['Content-Type']}, Size: {len(sitemap_resp.content)} bytes")
assert sitemap_resp.status_code == 200
assert 'application/xml' in sitemap_resp['Content-Type']
root = ET.fromstring(sitemap_resp.content)
ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
urls = root.findall('sm:url', ns)
print(f"  Sitemap parsed successfully: {len(urls)} URLs found.")
assert len(urls) == 14

# 3. Private Crawl Boundary & X-Robots-Tag
print("\n[AUDIT 3] Private vs Public Security Boundary Check")
for path in PRIVATE_PATHS:
    resp = client.get(path)
    tag = resp.headers.get('X-Robots-Tag', '')
    print(f"  {path:<35} Status: {resp.status_code} | X-Robots-Tag: {tag}")
    assert tag == 'noindex, nofollow', f"Path {path} did not return noindex, nofollow"

# 4. JSON-LD Schema Validation
print("\n[AUDIT 4] JSON-LD Schema Extraction & Validation")
from bs4 import BeautifulSoup
for path in PUBLIC_PATHS:
    resp = client.get(path)
    soup = BeautifulSoup(resp.content, 'html.parser')
    scripts = soup.find_all('script', type='application/ld+json')
    types_found = []
    for s in scripts:
        data = json.loads(s.string)
        if '@graph' in data:
            types_found.extend([item.get('@type') for item in data['@graph']])
        elif '@type' in data:
            types_found.append(data.get('@type'))
    print(f"  {path:<35} Schemas: {', '.join(types_found)}")
    assert len(types_found) > 0

print("\n" + "=" * 80)
print("AUDIT COMPLETE: 100% PRODUCTION VERIFIED")
print("=" * 80)
