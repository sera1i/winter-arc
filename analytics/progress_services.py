from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Count, Q
from zoneinfo import ZoneInfo

from arcs.models import Arc
from goals.models import Goal, Milestone
from tasks.models import Task
from habits.models import Habit, HabitCompletion
from journal.models import JournalEntry
from gamification.services import get_user_total_xp, get_user_rank
from analytics.models import ActivityEvent

def get_user_local_date(user):
    """Return user's local date based on profile timezone or configured TIME_ZONE."""
    try:
        from django.conf import settings
        tz_name = getattr(user.profile, 'timezone', None) if (user and hasattr(user, 'profile')) else None
        if not tz_name:
            tz_name = getattr(settings, 'TIME_ZONE', 'Asia/Kolkata')
        user_tz = ZoneInfo(tz_name)
    except Exception:
        user_tz = timezone.get_current_timezone()
    return timezone.now().astimezone(user_tz).date()

def calculate_arc_progress(arc):
    """
    Calculate deterministic Arc completion percentage based on concrete objectives.
    Formula:
      - If arc has goals:
          average of goals' progress_percentage
      - If arc has no goals:
          100% if status == 'COMPLETED', else 0%
    """
    if not arc:
        return 0
    if arc.status == 'COMPLETED':
        return 100
    goals = arc.goals.all()
    if not goals.exists():
        return 0
    total_goal_progress = sum(g.progress_percentage for g in goals)
    return int(total_goal_progress / goals.count())

def get_task_statistics(user, arc=None):
    """
    Return comprehensive task statistics scoped to user.
    If arc is provided, can filter by tasks attached to goals in that Arc or all user tasks.
    When arc is specified, if the arc has tasks linked via goals, returns those; 
    otherwise falls back to user's overall tasks so metrics are never empty when tasks exist.
    """
    user_tasks = Task.objects.filter(user=user).exclude(status='CANCELLED')
    if arc:
        arc_tasks = user_tasks.filter(goal__arc=arc)
        # If arc has specific tasks attached, use them; otherwise reflect user's tasks
        qs = arc_tasks if arc_tasks.exists() else user_tasks
        is_scoped_to_arc = arc_tasks.exists()
    else:
        qs = user_tasks
        is_scoped_to_arc = False

    total = qs.count()
    completed = qs.filter(status='COMPLETED').count()
    in_progress = qs.filter(status='IN_PROGRESS').count()
    pending = qs.filter(status='PENDING').count()

    today = get_user_local_date(user)
    # Overdue tasks: pending or in_progress with due_at date < today
    overdue = qs.filter(status__in=['PENDING', 'IN_PROGRESS'], due_at__date__lt=today).count()

    # Priority breakdown
    high_priority = qs.filter(priority=Task.PRIORITY_HIGH).count()
    med_priority = qs.filter(priority=Task.PRIORITY_MEDIUM).count()
    low_priority = qs.filter(priority=Task.PRIORITY_LOW).count()

    completion_rate = int((completed / total) * 100) if total > 0 else 0

    return {
        'total': total,
        'completed': completed,
        'in_progress': in_progress,
        'pending': pending,
        'overdue': overdue,
        'completion_rate': completion_rate,
        'high_priority': high_priority,
        'med_priority': med_priority,
        'low_priority': low_priority,
        'is_scoped_to_arc': is_scoped_to_arc,
    }

def get_habit_statistics(user):
    """
    Return habit statistics for user:
      - active count
      - completed today
      - overall completion rate over last 30 days
      - current longest streak
      - best historical streak
    """
    habits = Habit.objects.filter(user=user, is_archived=False).prefetch_related('completions')
    today = get_user_local_date(user)
    total_habits = habits.count()

    completed_today = 0
    current_streaks = []
    best_streaks = []

    for h in habits:
        if h.completions.filter(local_date=today).exists():
            completed_today += 1
        current_streaks.append(h.get_current_streak())
        best_streaks.append(h.best_streak)

    top_current_streak = max(current_streaks, default=0)
    top_best_streak = max(best_streaks, default=0)

    # 30-day consistency rate
    start_30 = today - timedelta(days=29)
    total_completions_30d = HabitCompletion.objects.filter(
        habit__user=user,
        habit__is_archived=False,
        local_date__gte=start_30,
        local_date__lte=today
    ).count()

    possible_completions_30d = total_habits * 30
    consistency_rate = int((total_completions_30d / possible_completions_30d) * 100) if possible_completions_30d > 0 else 0

    return {
        'total_habits': total_habits,
        'completed_today': completed_today,
        'top_current_streak': top_current_streak,
        'top_best_streak': top_best_streak,
        'completions_30d': total_completions_30d,
        'consistency_rate': consistency_rate,
    }

def get_activity_breakdown(user, days=7):
    """
    Aggregate daily activity data over the past N days.
    Returns:
      - labels: list of dates (strings formatted 'MMM DD')
      - tasks_data: list of completed task counts per day
      - habits_data: list of habit completions per day
      - total_events: int
    """
    today = get_user_local_date(user)
    labels = []
    tasks_data = []
    habits_data = []

    # Map out days
    date_list = [today - timedelta(days=i) for i in reversed(range(days))]

    # Efficient bulk query for tasks completed in range
    start_dt = timezone.make_aware(timezone.datetime.combine(date_list[0], timezone.datetime.min.time()))
    task_qs = Task.objects.filter(
        user=user,
        status='COMPLETED',
        completed_at__gte=start_dt
    ).values_list('completed_at', flat=True)

    task_day_counts = {}
    for dt in task_qs:
        if dt:
            d = dt.date()
            task_day_counts[d] = task_day_counts.get(d, 0) + 1

    # Bulk query for habits in range
    habit_qs = HabitCompletion.objects.filter(
        habit__user=user,
        local_date__gte=date_list[0],
        local_date__lte=today
    ).values('local_date').annotate(count=Count('id'))

    habit_day_counts = {item['local_date']: item['count'] for item in habit_qs}

    for d in date_list:
        labels.append(d.strftime('%b %d'))
        tasks_data.append(task_day_counts.get(d, 0))
        habits_data.append(habit_day_counts.get(d, 0))

    return {
        'labels': labels,
        'tasks_data': tasks_data,
        'habits_data': habits_data,
        'total_tasks_period': sum(tasks_data),
        'total_habits_period': sum(habits_data),
    }

def get_full_analytics_summary(user, arc_id=None):
    """
    Produce the complete unified analytics dataset for dashboard & analytics page.
    """
    user_arcs = Arc.objects.filter(user=user).exclude(status='ARCHIVED')
    selected_arc = None
    if arc_id:
        selected_arc = user_arcs.filter(pk=arc_id).first()
    if not selected_arc:
        selected_arc = user_arcs.filter(is_primary=True).first()

    arc_progress = calculate_arc_progress(selected_arc) if selected_arc else 0
    task_stats = get_task_statistics(user, arc=selected_arc)
    habit_stats = get_habit_statistics(user)
    rank_info = get_user_rank(user)
    activity_7d = get_activity_breakdown(user, days=7)
    activity_30d = get_activity_breakdown(user, days=30)
    
    # Recent activity events
    recent_events = ActivityEvent.objects.filter(user=user)
    if selected_arc:
        recent_events = recent_events.filter(Q(arc=selected_arc) | Q(arc__isnull=True))
    recent_events = recent_events.select_related('arc')[:8]

    # Goals breakdown if selected arc exists
    goals_data = []
    if selected_arc:
        for g in selected_arc.goals.all().prefetch_related('milestones'):
            total_m = g.milestones.count()
            completed_m = len([m for m in g.milestones.all() if m.is_completed])
            goals_data.append({
                'goal': g,
                'progress': g.progress_percentage,
                'total_milestones': total_m,
                'completed_milestones': completed_m,
            })

    return {
        'selected_arc': selected_arc,
        'user_arcs': user_arcs,
        'arc_progress': arc_progress,
        'task_stats': task_stats,
        'habit_stats': habit_stats,
        'rank_info': rank_info,
        'activity_7d': activity_7d,
        'activity_30d': activity_30d,
        'recent_events': recent_events,
        'goals_data': goals_data,
    }
