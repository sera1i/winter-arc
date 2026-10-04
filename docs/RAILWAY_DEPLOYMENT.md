# Railway Production Deployment Guide — Winter Arc

This guide details the exact architecture, services, environment variables, pre-deploy lifecycle, and deployment verification for the Winter Arc platform on Railway.

---

## 1. Architecture Topology

Winter Arc runs on Railway using a multi-service decoupled architecture:

```
                      ┌────────────────────────────┐
                      │    Railway Public Domain    │
                      │    (HTTPS / Edge Proxy)     │
                      └──────────────┬─────────────┘
                                     │ Dynamic $PORT
                                     ▼
                      ┌────────────────────────────┐
                      │    Web Service (Django)    │
                      │   Gunicorn 3w / 2t / 60s   │
                      │     WhiteNoise Statics     │
                      └───────┬─────────────┬──────┘
                              │             │
                ┌─────────────▼─┐         ┌─▼─────────────┐
                │   PostgreSQL  │         │  Redis Queue  │
                │   (Database)  │         │   & Caching   │
                └───────────────┘         └───────┬───────┘
                                                  │
                                  ┌───────────────┴───────────────┐
                                  │                               │
                                  ▼                               ▼
                      ┌──────────────────────┐        ┌──────────────────────┐
                      │    Celery Worker     │        │     Celery Beat      │
                      │   Background Tasks   │        │   Periodic Cron      │
                      └──────────────────────┘        └──────────────────────┘
```

---

## 2. Service Definitions & Start Commands

Configure three distinct Railway services connected to the repository:

### A. Web Service
- **Build Target**: Uses repository root [`Dockerfile`](file:///c:/Users/seral/OneDrive/Desktop/winter_arc/Dockerfile).
- **Pre-Deploy Command**:
  ```bash
  python manage.py migrate --noinput
  ```
  *(Runs isolated before new containers accept traffic; prevents migrations from running concurrently across multiple web/worker instances).*
- **Start Command**:
  ```bash
  gunicorn winter_arc.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --threads 2 --timeout 60
  ```
- **Static Assets**:
  Collected automatically during container build (`RUN python manage.py collectstatic --noinput`) and served in production via **WhiteNoise** (`CompressedManifestStaticFilesStorage`).
- **Healthcheck Path**: `/health/` or `/health/ready/`

### B. Celery Worker Service
- **Build Target**: Same Dockerfile / repo.
- **Start Command**:
  ```bash
  celery -A winter_arc worker --loglevel=info
  ```
- **Pre-Deploy Command**: None (handled by Web service).

### C. Celery Beat Service
- **Build Target**: Same Dockerfile / repo.
- **Start Command**:
  ```bash
  celery -A winter_arc beat --loglevel=info
  ```
- **Scaling**: Must run with exactly **1 replica** to prevent duplicate periodic task triggers.

---

## 3. Environment Variables Reference

Winter Arc strictly validates production variables. If `DJANGO_DEBUG=False`, starting the app with SQLite or missing/insecure keys will raise an explicit `ValueError` and halt execution.

### Railway Dynamic Service References

Configure these variables using Railway's reference syntax:

| Variable | Railway Reference Value | Purpose |
|---|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | PostgreSQL connection string |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` | Redis cache & Celery broker |

### Required Production Variables

| Variable | Example / Value | Description |
|---|---|---|
| `DJANGO_DEBUG` | `False` | Disables debug mode and activates security shields |
| `DJANGO_SECRET_KEY` | *(High-entropy 50+ char random string)* | Production Django cryptographic secret |
| `ALLOWED_HOSTS` | `.up.railway.app,yourcustomdomain.com` | Comma-separated list of allowed host domains |
| `CSRF_TRUSTED_ORIGINS` | `https://*.up.railway.app,https://yourcustomdomain.com` | Comma-separated list of HTTPS origins for CSRF |
| `CORS_ALLOWED_ORIGINS` | `https://*.up.railway.app,https://yourcustomdomain.com` | Comma-separated list of CORS origins |
| `DJANGO_TIME_ZONE` | `Asia/Kolkata` | Application baseline timezone |

### Optional / Integration Variables

| Variable | Default / Example | Purpose |
|---|---|---|
| `CELERY_TIMEZONE` | `Asia/Kolkata` | Celery beat schedule timezone |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` | SMTP email backend |
| `EMAIL_HOST` | `smtp.resend.com` / `smtp.sendgrid.net` | Outgoing SMTP server |
| `EMAIL_PORT` | `587` | Outgoing SMTP port |
| `EMAIL_USE_TLS` | `True` | TLS encryption |
| `EMAIL_HOST_USER` | `apikey` | SMTP account username |
| `EMAIL_HOST_PASSWORD` | *(SMTP API key / password)* | SMTP authentication secret |
| `DEFAULT_FROM_EMAIL` | `Winter Arc <notifications@yourdomain.com>` | Outgoing notification sender |

---

## 4. Production Security Hardening

When `DJANGO_DEBUG=False`, Winter Arc activates the following production headers and safeguards:

1. **Strict Production Validations**:
   - Refuses default/insecure secret keys.
   - Refuses SQLite databases (`DATABASE_URL` must point to PostgreSQL).
   - Refuses local memory cache or mock brokers (`REDIS_URL` must point to Redis).
2. **Transport Security (HSTS & SSL)**:
   - `SECURE_SSL_REDIRECT = True`
   - `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`
   - `SECURE_HSTS_SECONDS = 31536000` (1 year)
   - `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
   - `SECURE_HSTS_PRELOAD = True`
3. **Cookie Protection**:
   - `SESSION_COOKIE_SECURE = True`
   - `SESSION_COOKIE_HTTPONLY = True`
   - `CSRF_COOKIE_SECURE = True`
   - `CSRF_COOKIE_HTTPONLY = True`
   - `SECURE_REFERRER_POLICY = 'same-origin'`

---

## 5. Pre-Deployment Step-by-Step Procedure

1. **Create Railway Project**:
   - In Railway dashboard, create a new project.
2. **Provision Databases**:
   - Add **PostgreSQL** plugin.
   - Add **Redis** plugin.
3. **Deploy Web Service**:
   - Connect repository to Railway.
   - Set environment variables as documented above (`DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY`, dynamic `${{Postgres.DATABASE_URL}}`, dynamic `${{Redis.REDIS_URL}}`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`).
   - Configure pre-deploy command: `python manage.py migrate --noinput`.
   - Configure start command: `gunicorn winter_arc.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --threads 2 --timeout 60`.
4. **Deploy Background Services**:
   - Add second service from the same repo for **Celery Worker**:
     - Start command: `celery -A winter_arc worker --loglevel=info`.
     - Inherit shared environment variables.
   - Add third service from the same repo for **Celery Beat**:
     - Start command: `celery -A winter_arc beat --loglevel=info`.
     - Replicas set to **1**.
5. **Verify Endpoints**:
   - Liveness check: `GET https://your-railway-domain.up.railway.app/health/` (returns `{"status": "ok"}`).
   - Readiness check: `GET https://your-railway-domain.up.railway.app/health/ready/` (returns `{"status": "ready", "checks": {"database": "ok", "cache": "ok"}}`).
