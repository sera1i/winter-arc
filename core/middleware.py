import zoneinfo
from django.utils import timezone
from django.conf import settings


class TimezoneMiddleware:
    """
    Middleware that activates the user's configured timezone, browser-detected timezone,
    or project default TIME_ZONE for the current request.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = None

        # 1. Check authenticated user's profile timezone (cached in session to avoid per-request query)
        if request.user.is_authenticated:
            if hasattr(request, 'session'):
                tzname = request.session.get('user_timezone')
            if not tzname:
                try:
                    profile = getattr(request.user, 'profile', None)
                    if profile and profile.timezone:
                        tzname = profile.timezone
                        if hasattr(request, 'session'):
                            request.session['user_timezone'] = tzname
                except Exception:
                    pass

        # 2. Check browser-detected timezone from cookie
        if not tzname:
            tzname = request.COOKIES.get('django_timezone')

        # 3. Fallback to settings.TIME_ZONE
        if not tzname:
            tzname = getattr(settings, 'TIME_ZONE', 'Asia/Kolkata')

        try:
            timezone.activate(zoneinfo.ZoneInfo(tzname))
        except Exception:
            try:
                default_tz = getattr(settings, 'TIME_ZONE', 'UTC')
                timezone.activate(zoneinfo.ZoneInfo(default_tz))
            except Exception:
                timezone.deactivate()

        try:
            response = self.get_response(request)
        finally:
            timezone.deactivate()

        return response


class RobotsSecurityHeaderMiddleware:
    """
    Middleware that enforces defense-in-depth search engine boundary protection.
    Injects 'X-Robots-Tag: noindex, nofollow' HTTP header on:
      - All private authenticated routes (/arcs/, /goals/, /tasks/, /habits/, /journal/, /analytics/, /notifications/, /api/, /admin/, /health/, account actions)
      - All error and 404 responses
    Guarantees that public marketing and knowledge pages (/, /winter-arc/*, /guides/*, sitemap, robots)
    remain cleanly indexable without accidental noindex headers.
    """
    PRIVATE_PREFIXES = (
        '/accounts/dashboard/',
        '/accounts/profile/',
        '/accounts/password-reset/',
        '/accounts/logout/',
        '/accounts/login/',
        '/accounts/register/',
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
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        path = request.path_info
        if any(path.startswith(prefix) for prefix in self.PRIVATE_PREFIXES) or response.status_code >= 400:
            response['X-Robots-Tag'] = 'noindex, nofollow'

        return response
