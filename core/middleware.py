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

        # 1. Check authenticated user's profile timezone
        if request.user.is_authenticated:
            try:
                profile = getattr(request.user, 'profile', None)
                if profile and profile.timezone:
                    tzname = profile.timezone
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
