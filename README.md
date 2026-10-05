# Winter Arc

[![Django](https://img.shields.io/badge/Django-5.1+-092e20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4+-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Celery](https://img.shields.io/badge/Celery-5.4+-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)

A full-stack, battle-tested personal transformation, productivity, habit tracking, goal execution, fitness, journaling, and gamification platform designed for the 90-day seasonal discipline protocol ("Winter Arc").

---

## 🌟 Core Features

- **🛡️ Arc Lifecycle Management**: Define your primary transformation arc, set operational start/target dates, and track completion progress across custom horizons.
- **🎯 Goals & Milestones**: Hierarchical goal-setting connected directly to progressive milestones with percentage-based completion logic.
- **⚡ Task Horizon**: Prioritized task tracking (High, Medium, Low) with smart filtering, due dates, and recurrence engines.
- **🔥 Habit & Streak Engine**: Habit tracking with automated streak calculation, temporal timezone resilience, and historical bests.
- **📖 Private Journaling & Daily Reflections**: Markdown-friendly personal check-ins with mood indicators and one-time XP rewards (+40 XP).
- **⏱️ Deep Work & Workout Logs**: Time-tracked study sessions and workout logging integrated into user performance reports.
- **📊 Analytics & Horizon Charts**: 7-day execution horizons, 30-day consistency metrics, task success rates, and live activity breakdowns.
- **⚔️ Gamification & Ranks**: Real-time XP awarding, activity telemetry, idempotent rank escalations (Recruit &rarr; Sentinel &rarr; Ranger &rarr; Warden), and achievement unlocks.
- **🔔 Notification Daemon**: Periodic Celery tasks for deadline warnings, habit reminders, and streak milestone alerts with user preference suppressions.
- **🌐 REST API**: Comprehensive Django REST Framework endpoints with Token Authentication, rate limiting, and OpenAPI schemas.

---

## 🏗️ Architecture & Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.12, Django 5.x, Django REST Framework (DRF) |
| **Frontend** | Django Templates, Tailwind CSS (Custom Dark Theme), Vanilla JavaScript |
| **Database** | PostgreSQL (Production) / SQLite3 (Development fallback) |
| **Queue & Cache** | Celery 5.4, Redis, django-redis |
| **Static Serving**| WhiteNoise (`CompressedManifestStaticFilesStorage`) |
| **Production WSGI**| Gunicorn (`gthread` worker mode) |
| **Deployment** | Docker, Railway (`https://arcinwinter.up.railway.app`) |

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- Python 3.12+
- Node.js 18+ (for compiling Tailwind CSS)
- Redis server (or Docker for Redis/Postgres)

### 2. Setup Virtual Environment
```bash
git clone https://github.com/your-username/winter_arc.git
cd winter_arc

python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
npm install
```

### 3. Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in the basic development variables:
```env
DJANGO_SECRET_KEY=replace-with-a-local-development-secret
DJANGO_DEBUG=True
DJANGO_TIME_ZONE=Asia/Kolkata
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0
```

### 4. Build Styles & Run Migrations
```bash
# Build Tailwind CSS
npm run tailwind:build

# Apply database migrations
python manage.py migrate

# Create a local superuser
python manage.py createsuperuser
```

### 5. Launch the Application
```bash
# In Terminal 1: Django Web Server
python manage.py runserver 8000

# In Terminal 2: Celery Worker
celery -A winter_arc worker --loglevel=info

# In Terminal 3: Celery Beat (Periodic Scheduler)
celery -A winter_arc beat --loglevel=info
```
Visit `http://localhost:8000` to start your Arc.

---

## 🧪 Testing & Verification

Winter Arc maintains a comprehensive test suite (130+ unit, integration, and security tests):

```bash
# Run full project test suite
python manage.py test --keepdb

# Verify production deployment readiness
python manage.py check --deploy

# Check static assets post-processing
python manage.py collectstatic --dry-run
```

---

## ☁️ Production Deployment (Railway)

The project is pre-configured and hardened for production deployment on **Railway**.

### Architecture on Railway
1. **Web Service**: Gunicorn WSGI running on dynamic `$PORT` with WhiteNoise static serving.
   - Pre-deploy Command: `python manage.py migrate --noinput`
   - Start Command: `gunicorn winter_arc.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --threads 2 --timeout 60`
   - Healthcheck Endpoint: `/health/`
2. **Celery Worker**: Background task executor (`celery -A winter_arc worker --loglevel=info`).
3. **Celery Beat**: Periodic cron scheduler (`celery -A winter_arc beat --loglevel=info`).
4. **Railway Plugins**: PostgreSQL (`${{Postgres.DATABASE_URL}}`) and Redis (`${{Redis.REDIS_URL}}`).

For complete step-by-step instructions and environment variable configurations, refer to the [Railway Deployment Guide](docs/RAILWAY_DEPLOYMENT.md).

---

## 🔒 Security & Reliability

- **Strict Production Gateways**: Rejects SQLite and insecure secret keys in production when `DJANGO_DEBUG=False`.
- **Exempt Health Probes**: Health endpoints (`/health/`, `/health/ready/`) are exempted from SSL redirect for load balancers and Railway probes while keeping all user traffic forced through HTTPS.
- **OWASP Hardened**: Full HSTS (31536000s with subdomains and preload), secure CSRF/session cookies, `same-origin` referrer policy, X-Frame DENY, and XSS filtering.
- **Rate Limiting**: Automated API throttles for anonymous and authenticated traffic.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
