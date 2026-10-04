from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache


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

