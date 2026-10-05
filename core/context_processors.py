from django.conf import settings


def seo_context(request):
    """
    Supplies the normalized canonical site URL to all templates.
    """
    return {
        'SITE_URL': getattr(settings, 'SITE_URL', 'https://arcinwinter.up.railway.app').rstrip('/'),
    }
