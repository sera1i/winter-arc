from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.db import connection
from django.core.cache import cache
from django.conf import settings


def health_liveness(request):
    """
    Lightweight liveness probe for Railway web service.
    Returns HTTP 200 if the Python / Django process is alive and responsive.
    """
    return JsonResponse({'status': 'ok', 'service': 'winter-arc'}, status=200)


def health_readiness(request):
    """
    Readiness probe for Railway web service.
    Verifies that the database and cache (Redis) connections are available.
    Does not expose sensitive credentials or database host names.
    """
    checks = {}
    is_ready = True

    # 1. Database readiness check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()
        checks['database'] = 'ok'
    except Exception:
        checks['database'] = 'unavailable'
        is_ready = False

    # 2. Cache / Redis readiness check
    try:
        cache.set('_health_ping', 'pong', timeout=10)
        val = cache.get('_health_ping')
        if val == 'pong':
            checks['cache'] = 'ok'
        else:
            checks['cache'] = 'degraded'
            is_ready = False
    except Exception:
        checks['cache'] = 'unavailable'
        is_ready = False

    status_code = 200 if is_ready else 503
    return JsonResponse({
        'status': 'ready' if is_ready else 'not_ready',
        'checks': checks
    }, status=status_code)


def robots_txt(request):
    """
    Serves plain-text robots.txt directive adhering to RFC 9309.
    Explicitly distinguishes search crawlers (Googlebot, Bingbot, OAI-SearchBot)
    from AI model-training crawlers (GPTBot), shielding private application data
    while ensuring public discoverability and asset rendering.
    """
    site_url = getattr(settings, 'SITE_URL', 'https://arcinwinter.up.railway.app').rstrip('/')
    sitemap_url = f"{site_url}/sitemap.xml"

    disallowed_private_routes = [
        "Disallow: /accounts/dashboard/",
        "Disallow: /accounts/profile/",
        "Disallow: /accounts/password-reset/",
        "Disallow: /accounts/logout/",
        "Disallow: /dashboard/",
        "Disallow: /arcs/",
        "Disallow: /goals/",
        "Disallow: /tasks/",
        "Disallow: /habits/",
        "Disallow: /journal/",
        "Disallow: /analytics/",
        "Disallow: /notifications/",
        "Disallow: /api/",
        "Disallow: /admin/",
        "Disallow: /health/",
    ]

    def build_agent_block(agent_name):
        return [
            f"User-agent: {agent_name}",
            "Allow: /",
            "Allow: /static/",
            "Allow: /media/",
        ] + disallowed_private_routes

    lines = []
    # 1. Googlebot
    lines.extend(build_agent_block("Googlebot"))
    lines.append("")

    # 2. Bingbot
    lines.extend(build_agent_block("Bingbot"))
    lines.append("")

    # 3. OAI-SearchBot (OpenAI Search indexer)
    lines.extend(build_agent_block("OAI-SearchBot"))
    lines.append("")

    # 4. GPTBot (LLM Training crawler - kept conceptually separate from search indexing)
    lines.extend([
        "# AI Model Training crawler (prohibited from training on proprietary application content)",
        "User-agent: GPTBot",
        "Disallow: /",
        "",
    ])

    # 5. Generic fallback for all other crawlers
    lines.extend(build_agent_block("*"))
    lines.append("")

    # 6. Canonical Sitemap pointer
    lines.append(f"Sitemap: {sitemap_url}")
    lines.append("")

    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    """
    Generates standard XML Sitemap (sitemaps.org 0.9 schema)
    containing strictly canonical public indexable URLs.
    Never exposes private user data or authenticated routes.
    """
    site_url = getattr(settings, 'SITE_URL', 'https://arcinwinter.up.railway.app').rstrip('/')

    # Extensible public canonical URL registry for future Phase 3 SEO pages
    public_entries = [
        {
            'loc': f"{site_url}/",
            'changefreq': 'weekly',
            'priority': '1.0',
        },
    ]

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for entry in public_entries:
        xml_lines.append('  <url>')
        xml_lines.append(f"    <loc>{entry['loc']}</loc>")
        xml_lines.append(f"    <changefreq>{entry['changefreq']}</changefreq>")
        xml_lines.append(f"    <priority>{entry['priority']}</priority>")
        xml_lines.append('  </url>')
    xml_lines.append('</urlset>')

    return HttpResponse("\n".join(xml_lines), content_type="application/xml; charset=utf-8")


def custom_404(request, exception=None):
    """
    SEO-friendly, non-indexable 404 handler that preserves true HTTP 404 status.
    Renders Winter Arc branded 404 page directing users to sanctuary.
    """
    return render(request, '404.html', status=404)

