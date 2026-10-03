import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'winter_arc.settings')
django.setup()

from django.contrib.auth import get_user_model
from arcs.models import Arc
from goals.models import Goal, Milestone
from tasks.models import Task
from habits.models import Habit, HabitCompletion
from gamification.models import XPEvent, Achievement, UserAchievement
from analytics.models import ActivityEvent

User = get_user_model()
print('=== USERS ===')
for u in User.objects.all():
    print(f'User ID={u.id}, username={u.username}')

print('\n=== HABITS ===')
for h in Habit.objects.all().order_by('id'):
    print(f'Habit ID={h.id}, User={h.user.username}, Name="{h.name}", Archived={h.is_archived}, Created={h.created_at}')

print('\n=== HABIT COMPLETIONS ===')
for c in HabitCompletion.objects.all().order_by('id'):
    print(f'Comp ID={c.id}, HabitID={c.habit_id}, HabitName="{c.habit.name}", Date={c.local_date}, Created={c.completed_at}')

print('\n=== XP EVENTS ===')
for x in XPEvent.objects.all().order_by('id'):
    print(f'XP ID={x.id}, User={x.user.username}, SourceType={x.source_type}, SourceID={x.source_id}, Amount={x.amount}, Created={x.created_at}')

print('\n=== ACTIVITY EVENTS ===')
for a in ActivityEvent.objects.all().order_by('id'):
    print(f'Act ID={a.id}, User={a.user.username}, Type={a.event_type}, Title="{a.title}", SourceType={a.source_type}, SourceID={a.source_id}, Created={a.created_at}')

print('\n=== TASKS ===')
for t in Task.objects.all().order_by('id'):
    print(f'Task ID={t.id}, User={t.user.username}, Title="{t.title}", GoalID={t.goal_id}, GoalArc={t.goal.arc_id if t.goal else None}, Status={t.status}, Created={t.created_at}, Completed={t.completed_at}')

print('\n=== GOALS ===')
for g in Goal.objects.all().order_by('id'):
    print(f'Goal ID={g.id}, User={g.user.username}, Title="{g.title}", ArcID={g.arc_id}, Status={g.status}')

print('\n=== MILESTONES ===')
for m in Milestone.objects.all().order_by('id'):
    print(f'Milestone ID={m.id}, GoalID={m.goal_id}, Title="{m.title}", CompletedAt={m.completed_at}')

print('\n=== ARCS ===')
for arc in Arc.objects.all().order_by('id'):
    print(f'Arc ID={arc.id}, User={arc.user.username}, Name="{arc.name}", Status={arc.status}, IsPrimary={arc.is_primary}')
