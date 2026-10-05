import os
import django
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'winter_arc.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import Profile
from arcs.models import Arc
from goals.models import Goal, Milestone
from tasks.models import Task
from habits.models import Habit
from journal.models import JournalEntry
from notifications.models import Notification

User = get_user_model()

user, _ = User.objects.get_or_create(username='browseruser1')
user.set_password('Password123!')
user.save()

profile, _ = Profile.objects.get_or_create(user=user)
profile.timezone = 'Asia/Kolkata'
profile.save()

# Ensure Arc
arc, created = Arc.objects.get_or_create(
    user=user,
    name="Winter Arc Protocol 2026",
    defaults={
        'objective': 'Forging physical and mental endurance through daily protocols.',
        'start_date': date.today() - timedelta(days=5),
        'end_date': date.today() + timedelta(days=85),
        'status': 'ACTIVE',
        'is_primary': True,
    }
)
if not created and not arc.is_primary:
    arc.is_primary = True
    arc.save()

# Ensure Goal
goal, _ = Goal.objects.get_or_create(
    user=user,
    arc=arc,
    title="Cold Resistance & Physical Mastery",
    defaults={
        'category': 'HEALTH',
        'priority': 1,
        'deadline': date.today() + timedelta(days=30),
        'target_value': 100.0,
        'current_value': 40.0,
        'unit': 'sessions'
    }
)

# Ensure Milestone
Milestone.objects.get_or_create(
    goal=goal,
    title="Sub-zero 5-Minute Plunge",
    defaults={
        'due_date': date.today() + timedelta(days=14),
        'target_value': 5.0
    }
)

# Ensure Task
Task.objects.get_or_create(
    user=user,
    title="Execute 100 Pushups at Dawn",
    defaults={
        'goal': goal,
        'priority': Task.PRIORITY_HIGH,
        'status': 'PENDING'
    }
)

# Ensure Habit
Habit.objects.get_or_create(
    user=user,
    name="Hydration Protocol (4L Water)",
    defaults={
        'frequency': 'DAILY',
        'active_from': date.today() - timedelta(days=10),
        'is_archived': False
    }
)

# Ensure Journal
JournalEntry.objects.get_or_create(
    user=user,
    local_date=date.today(),
    defaults={
        'mood': 5,
        'energy': 5,
        'sleep_hours': 8.0,
        'reflection': 'Discipline is the bridge between goals and accomplishment.',
        'notes': 'All daily directives met ahead of twilight.'
    }
)

# Ensure Notification
Notification.objects.get_or_create(
    user=user,
    dedup_key="welcome-directive-browseruser1",
    defaults={
        'title': "Directive Confirmed",
        'message': 'Your daily habit streak has been verified. Continue forward.',
        'notification_type': Notification.TYPE_STREAK_MILESTONE,
    }
)

print(f"Browser fixtures ready! User: {user.username}, Arc ID: {arc.pk}, Goal ID: {goal.pk}")
