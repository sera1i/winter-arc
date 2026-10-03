import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'winter_arc.settings')
django.setup()

from django.contrib.auth import get_user_model
from habits.models import Habit, HabitCompletion
from gamification.models import XPEvent
from analytics.models import ActivityEvent

User = get_user_model()
u = User.objects.filter(username='browseruser').first()
if u:
    print('=== HABITS FOR browseruser ===')
    for h in Habit.objects.filter(user=u):
        print(f'ID={h.id}, Name="{h.name}", is_archived={h.is_archived}, Created={h.created_at}')

    print('\n=== HABIT COMPLETIONS FOR browseruser ===')
    for c in HabitCompletion.objects.filter(habit__user=u):
        print(f'ID={c.id}, HabitID={c.habit_id}, Name="{c.habit.name}", Date={c.local_date}, Created={c.completed_at}')

    print('\n=== XP EVENTS FOR browseruser ===')
    for x in XPEvent.objects.filter(user=u):
        print(f'ID={x.id}, SourceType={x.source_type}, SourceID={x.source_id}, Amount={x.amount}, Created={x.created_at}')

    print('\n=== ACTIVITY EVENTS FOR browseruser ===')
    for a in ActivityEvent.objects.filter(user=u):
        print(f'ID={a.id}, EventType={a.event_type}, Title="{a.title}", SourceType={a.source_type}, SourceID={a.source_id}, Created={a.created_at}')
else:
    print("browseruser not found!")
