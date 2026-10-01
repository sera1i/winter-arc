# Winter Arc

A full-stack personal transformation, productivity, habit, goal, study, fitness, journaling, analytics, and gamification platform.

## Features
- Winter Arc Lifecycle Management
- Goals and Milestones tracking
- Tasks with recurrences
- Habit tracking with streak calculations
- Daily Check-ins & Private Journaling
- Study and Workout Session tracking
- Comprehensive Analytics Dashboard
- Gamification (XP, Achievements)
- Configurable Notifications

## Architecture
- **Backend:** Python + Django
- **API:** Django REST Framework (DRF)
- **Frontend:** Django Templates + Tailwind CSS + Vanilla JavaScript
- **Database:** PostgreSQL
- **Background Tasks:** Celery + Redis

## Prerequisites
- Docker and Docker Compose
- Python 3.12+ (for local development without Docker)

## Setup and Installation

### Using Docker (Recommended)
1. Clone the repository
2. Copy .env.example to .env and fill in required secrets.
3. Run docker-compose up --build -d
4. Run migrations: docker-compose exec web python manage.py migrate
5. Access the application at http://localhost:8000

### Local Development (Virtual Environment)
1. Create a virtual environment: python -m venv venv
2. Activate it: .\venv\Scripts\Activate (Windows) or source venv/bin/activate (macOS/Linux)
3. Install dependencies: pip install -r requirements.txt
4. Run a local PostgreSQL and Redis instance.
5. Setup your .env file.
6. Apply migrations: python manage.py migrate
7. Start server: python manage.py runserver
8. Start celery worker: celery -A winter_arc worker -l info
9. Start celery beat: celery -A winter_arc beat -l info

