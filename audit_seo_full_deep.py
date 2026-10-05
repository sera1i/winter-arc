import os
import re
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'winter_arc.settings')
django.setup()

from django.urls import resolve, Resolver404, reverse
from bs4 import BeautifulSoup
from django.test import RequestFactory
from core.seo_views import (
    pillar_view, rules_view, habits_view, challenge_view,
    templates_view, for_students_view, for_fitness_view,
    for_career_view, guides_index_view, guide_how_to_start_view,
    guide_build_habits_view, guide_daily_routine_view, guide_goals_view
)
from accounts.views import landing_view

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

factory = RequestFactory()

pages = [
    ('/', landing_view, 'home'),
    ('/winter-arc/', pillar_view, 'winter_arc_pillar'),
    ('/winter-arc/rules/', rules_view, 'winter_arc_rules'),
    ('/winter-arc/habits/', habits_view, 'winter_arc_habits'),
    ('/winter-arc/challenge/', challenge_view, 'winter_arc_challenge'),
    ('/winter-arc/templates/', templates_view, 'winter_arc_templates'),
    ('/winter-arc/for-students/', for_students_view, 'winter_arc_for_students'),
    ('/winter-arc/for-fitness/', for_fitness_view, 'winter_arc_for_fitness'),
    ('/winter-arc/for-career/', for_career_view, 'winter_arc_for_career'),
    ('/guides/', guides_index_view, 'guides_index'),
    ('/guides/how-to-start-a-winter-arc/', guide_how_to_start_view, 'guide_how_to_start'),
    ('/guides/how-to-build-winter-arc-habits/', guide_build_habits_view, 'guide_build_habits'),
    ('/guides/winter-arc-daily-routine/', guide_daily_routine_view, 'guide_daily_routine'),
    ('/guides/winter-arc-goals/', guide_goals_view, 'guide_goals'),
]

titles = {}
descriptions = {}

print("--- 1. RENDERING & METADATA & LINKS AUDIT ---")
for path, view_func, url_name in pages:
    req = factory.get(path)
    # mock session and user
    from django.contrib.auth.models import AnonymousUser
    req.user = AnonymousUser()
    from django.contrib.sessions.middleware import SessionMiddleware
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(req)
    req.session.save()

    resp = view_func(req)
    html = resp.content.decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')

    # Title
    t_tag = soup.find('title')
    title = t_tag.text.strip() if t_tag else 'NO TITLE'
    titles[path] = title

    # Description
    d_tag = soup.find('meta', attrs={'name': 'description'})
    desc = d_tag['content'].strip() if d_tag else 'NO DESC'
    descriptions[path] = desc

    # Links audit
    links = soup.find_all('a', href=True)
    bad_links = []
    for l in links:
        href = l['href']
        if href.startswith('#') or href.startswith('mailto:') or href.startswith('javascript:'):
            continue
        if href.startswith('http://') or href.startswith('https://'):
            if 'arcinwinter.up.railway.app' in href or '127.0.0.1' in href or 'localhost' in href:
                # internal full url, extract path
                clean_path = re.sub(r'https?://[^/]+', '', href)
                try:
                    resolve(clean_path or '/')
                except Resolver404:
                    bad_links.append((href, 'Unresolvable absolute internal link'))
            continue
        # Relative link
        try:
            # resolve expects path
            clean_path = href.split('?')[0].split('#')[0]
            resolve(clean_path)
        except Resolver404:
            bad_links.append((href, 'Unresolvable path'))

    print(f"[{path}]")
    print(f"  Title: {title}")
    print(f"  Desc:  {desc[:60]}...")
    if bad_links:
        print(f"  [ERROR] Bad links: {bad_links}")
    else:
        print(f"  All {len(links)} links resolved successfully.")

print("\n--- 2. TITLE & DESCRIPTION UNIQUENESS ---")
dup_titles = [t for t in set(titles.values()) if list(titles.values()).count(t) > 1]
dup_descs = [d for d in set(descriptions.values()) if list(descriptions.values()).count(d) > 1]
print(f"Duplicate titles: {dup_titles}")
print(f"Duplicate descriptions: {dup_descs}")
