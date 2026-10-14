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

def get_user_timezone(user):
    """Return user's ZoneInfo based on profile timezone or configured TIME_ZONE."""
    try:
        from django.conf import settings
        tz_name = getattr(user.profile, 'timezone', None) if (user and hasattr(user, 'profile')) else None
        if not tz_name:
            tz_name = getattr(settings, 'TIME_ZONE', 'Asia/Kolkata')
        return ZoneInfo(tz_name)
    except Exception:
        return timezone.get_current_timezone()

def get_user_local_date(user):
    """Return user's local date based on profile timezone or configured TIME_ZONE."""
    user_tz = get_user_timezone(user)
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

    today = get_user_local_date(user)
    stats = qs.aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='COMPLETED')),
        in_progress=Count('id', filter=Q(status='IN_PROGRESS')),
        pending=Count('id', filter=Q(status='PENDING')),
        overdue=Count('id', filter=Q(status__in=['PENDING', 'IN_PROGRESS'], due_at__date__lt=today)),
        high_priority=Count('id', filter=Q(priority=Task.PRIORITY_HIGH)),
        med_priority=Count('id', filter=Q(priority=Task.PRIORITY_MEDIUM)),
        low_priority=Count('id', filter=Q(priority=Task.PRIORITY_LOW)),
    )
    total = stats['total'] or 0
    completed = stats['completed'] or 0
    in_progress = stats['in_progress'] or 0
    pending = stats['pending'] or 0
    overdue = stats['overdue'] or 0
    high_priority = stats['high_priority'] or 0
    med_priority = stats['med_priority'] or 0
    low_priority = stats['low_priority'] or 0

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
    habits = list(Habit.objects.filter(user=user, is_archived=False).prefetch_related('completions'))
    today = get_user_local_date(user)
    total_habits = len(habits)

    completed_today = 0
    current_streaks = []
    best_streaks = []

    for h in habits:
        completed_dates = {c.local_date for c in h.completions.all()}
        if today in completed_dates:
            completed_today += 1
        current_streaks.append(h.get_current_streak(today=today, completed_dates=completed_dates))
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

    user_tz = get_user_timezone(user)

    # Efficient bulk query for tasks completed in range
    # Start of the earliest day in user's timezone converted to UTC / aware dt
    start_dt = timezone.datetime.combine(date_list[0], timezone.datetime.min.time(), tzinfo=user_tz)
    task_qs = Task.objects.filter(
        user=user,
        status='COMPLETED',
        completed_at__gte=start_dt
    ).values_list('completed_at', flat=True)

    task_day_counts = {}
    for dt in task_qs:
        if dt:
            d = dt.astimezone(user_tz).date()
            task_day_counts[d] = task_day_counts.get(d, 0) + 1

    # Bulk query for habits in range
    habit_qs = HabitCompletion.objects.filter(
        habit__user=user,
        local_date__gte=date_list[0],
        local_date__lte=today
    ).values('local_date').annotate(count=Count('id'))

    habit_day_counts = {item['local_date']: item['count'] for item in habit_qs}

    daily_items = []
    for d in date_list:
        label = d.strftime('%b %d')
        t_count = task_day_counts.get(d, 0)
        h_count = habit_day_counts.get(d, 0)
        labels.append(label)
        tasks_data.append(t_count)
        habits_data.append(h_count)
        daily_items.append({
            'label': label,
            'date': d,
            'tasks': t_count,
            'habits': h_count,
        })

    return {
        'labels': labels,
        'tasks_data': tasks_data,
        'habits_data': habits_data,
        'daily_items': daily_items,
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
            milestones = list(g.milestones.all())
            total_m = len(milestones)
            completed_m = sum(1 for m in milestones if m.is_completed)
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


def get_user_sync_state(user, arc=None, goal=None):
    """
    Build an authoritative, real-time synchronization payload for the user.
    """
    today = get_user_local_date(user)
    total_xp = get_user_total_xp(user)
    rank_info = get_user_rank(user)

    user_tasks = Task.objects.filter(user=user)
    today_completed_tasks = user_tasks.filter(status='COMPLETED', completed_at__date=today).count()
    total_pending_count = user_tasks.filter(status__in=['PENDING', 'IN_PROGRESS']).count()
    task_counts = user_tasks.exclude(status='CANCELLED').aggregate(
        pending=Count('id', filter=Q(status='PENDING')),
        inprogress=Count('id', filter=Q(status='IN_PROGRESS')),
        completed=Count('id', filter=Q(status='COMPLETED')),
        total=Count('id')
    )

    habit_stats = get_habit_statistics(user)

    target_arc = arc
    if not target_arc:
        target_arc = Arc.objects.filter(user=user, is_primary=True).exclude(status='ARCHIVED').first()
    arc_prog = calculate_arc_progress(target_arc) if target_arc else 0

    goal_prog = goal.progress_percentage if goal else None
    goal_status = goal.status if goal else None

    return {
        'total_xp': total_xp,
        'rank': {
            'current_rank': rank_info['current_rank'],
            'current_level': rank_info['current_level'],
            'next_rank': rank_info['next_rank'],
            'xp_to_next': rank_info['xp_to_next'],
            'progress_percentage': rank_info['progress_percentage'],
            'is_max_rank': rank_info['is_max_rank'],
        },
        'tasks': {
            'today_completed': today_completed_tasks,
            'total_pending': total_pending_count,
            'pending': task_counts['pending'] or 0,
            'inprogress': task_counts['inprogress'] or 0,
            'completed': task_counts['completed'] or 0,
            'total': task_counts['total'] or 0,
        },
        'habits': {
            'completed_today': habit_stats['completed_today'],
            'total_habits': habit_stats['total_habits'],
            'top_streak': habit_stats['top_current_streak'],
            'best_streak': habit_stats['top_best_streak'],
        },
        'arc': {
            'id': target_arc.pk if target_arc else None,
            'progress': arc_prog,
        } if target_arc else None,
        'goal': {
            'id': goal.pk if goal else None,
            'progress': goal_prog,
            'status': goal_status,
        } if goal else None,
    }
