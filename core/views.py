import logging
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger('core')


def liveness_check(request):
    """
    Lightweight healthcheck endpoint for load balancers / orchestrators.
    Returns HTTP 200 immediately if process is alive.
    """
    return JsonResponse({
        "status": "live",
        "timestamp": timezone.now().isoformat(),
    }, status=200)


def readiness_check(request):
    """
    Readiness healthcheck endpoint verifying external dependencies:
    - Database connection
    - Cache / Redis connection
    Returns HTTP 200 if all dependencies are accessible, 503 otherwise.
    Never exposes internal tracebacks or secrets.
    """
    checks = {
        "database": False,
        "cache": False,
    }

    # 1. Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()
            if row and row[0] == 1:
                checks["database"] = True
    except Exception as exc:
        logger.warning("Readiness probe database check failed: %s", exc)
        checks["database"] = False

    # 2. Cache / Redis check
    try:
        test_key = "__readiness_probe__"
        cache.set(test_key, "ok", timeout=10)
        val = cache.get(test_key)
        if val == "ok":
            checks["cache"] = True
    except Exception as exc:
        logger.warning("Readiness probe cache check failed: %s", exc)
        checks["cache"] = False

    all_ready = all(checks.values())
    status_code = 200 if all_ready else 503

    return JsonResponse({
        "status": "ready" if all_ready else "unhealthy",
        "timestamp": timezone.now().isoformat(),
        "components": checks,
    }, status=status_code)
