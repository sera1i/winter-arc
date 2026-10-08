from django.conf import settings


def seo_context(request):
    """
    Supplies the normalized canonical site URL and search engine verification tokens to all templates.
    """
    return {
        'SITE_URL': getattr(settings, 'SITE_URL', 'https://arcinwinter.up.railway.app').rstrip('/'),
        'GOOGLE_SITE_VERIFICATION': getattr(settings, 'GOOGLE_SITE_VERIFICATION', ''),
        'BING_SITE_VERIFICATION': getattr(settings, 'BING_SITE_VERIFICATION', ''),
    }
