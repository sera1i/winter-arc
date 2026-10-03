import logging
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.utils import timezone
from django.contrib.auth import get_user_model
from celery import shared_task

from .models import Notification
from .services import create_notification
from tasks.models import Task
from habits.models import Habit, HabitCompletion
from goals.models import Goal
from arcs.models import Arc

logger = logging.getLogger(__name__)
User = get_user_model()

def _get_user_local_now(user):
    """Return user's localized current datetime."""
    try:
        from django.conf import settings
        tz_name = getattr(user.profile, 'timezone', None) if (user and hasattr(user, 'profile')) else None
        if not tz_name:
            tz_name = getattr(settings, 'TIME_ZONE', 'Asia/Kolkata')
        user_tz = ZoneInfo(tz_name)
    except Exception:
        user_tz = timezone.get_current_timezone()
    return timezone.now().astimezone(user_tz)

def _get_user_local_date(user):
    """Return user's localized date."""
    return _get_user_local_now(user).date()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_due_task_notifications(self):
    """
    Check for tasks that are due soon (within the next 24 hours) or overdue.
    Safe against retries; enforces deterministic deduplication.
    """
    logger.info("Executing process_due_task_notifications...")
    count_created = 0
    now_utc = timezone.now()

    # Active pending/in-progress tasks with due dates
    tasks = Task.objects.filter(
        status__in=['PENDING', 'IN_PROGRESS'],
        due_at__isnull=False
    ).select_related('user', 'user__profile')

    for task in tasks:
        user = task.user
        local_now = _get_user_local_now(user)
        task_due_local = task.due_at.astimezone(local_now.tzinfo)

        # 1. Check Overdue
        if task.due_at < now_utc:
            due_date_str = task_due_local.strftime('%Y-%m-%d')
            dedup_key = f"task_overdue_{task.pk}_{due_date_str}"
            n, created = create_notification(
                user=user,
                notification_type=Notification.TYPE_TASK_OVERDUE,
                title="Task Overdue",
                message=f'"{task.title}" was due on {task_due_local.strftime("%b %d, %H:%M")}. Hold the line and finish it.',
                dedup_key=dedup_key,
                source_type='task',
                source_id=task.pk,
                scheduled_for=task.due_at
            )
            if created:
                count_created += 1

        # 2. Check Due Soon (due within next 24 hours)
        elif task.due_at <= now_utc + timedelta(hours=24):
            due_date_str = task_due_local.strftime('%Y-%m-%d')
            dedup_key = f"task_due_soon_{task.pk}_{due_date_str}"
            n, created = create_notification(
                user=user,
                notification_type=Notification.TYPE_TASK_DUE_SOON,
                title="Task Due Soon",
                message=f'"{task.title}" is due at {task_due_local.strftime("%H:%M today" if task_due_local.date() == local_now.date() else "%b %d, %H:%M")}.',
                dedup_key=dedup_key,
                source_type='task',
                source_id=task.pk,
                scheduled_for=task.due_at
            )
            if created:
                count_created += 1

    logger.info(f"process_due_task_notifications complete. Created {count_created} notifications.")
    return count_created


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_habit_reminders(self):
    """
    Check for active habits that have not been completed today in the user's local timezone.
    Suppresses archived habits and habits already marked completed today.
    """
    logger.info("Executing process_habit_reminders...")
    count_created = 0

    active_habits = Habit.objects.filter(is_archived=False).select_related('user', 'user__profile')
    for habit in active_habits:
        user = habit.user
        local_date = _get_user_local_date(user)

        # Check if habit was already completed today
        is_done = HabitCompletion.objects.filter(habit=habit, local_date=local_date).exists()
        if not is_done:
            dedup_key = f"habit_reminder_{habit.pk}_{local_date}"
            n, created = create_notification(
                user=user,
                notification_type=Notification.TYPE_HABIT_REMINDER,
                title="Habit Reminder",
                message=f'The beacon for "{habit.name}" remains unlit today. Light the fire before midnight.',
                dedup_key=dedup_key,
                source_type='habit',
                source_id=habit.pk
            )
            if created:
                count_created += 1

    logger.info(f"process_habit_reminders complete. Created {count_created} notifications.")
    return count_created


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_deadline_notifications(self):
    """
    Check for Goal and Arc deadlines approaching (within 7 days) or past due.
    Suppresses completed or archived entities.
    """
    logger.info("Executing process_deadline_notifications...")
    count_created = 0

    # 1. Goals
    active_goals = Goal.objects.filter(
        deadline__isnull=False
    ).exclude(status__in=['COMPLETED', 'CANCELLED']).select_related('user', 'user__profile')

    for goal in active_goals:
        user = goal.user
        local_date = _get_user_local_date(user)
        days_left = (goal.deadline - local_date).days

        if 0 <= days_left <= 7:
            dedup_key = f"goal_deadline_{goal.pk}_{goal.deadline}"
            n, created = create_notification(
                user=user,
                notification_type=Notification.TYPE_GOAL_DEADLINE,
                title="Goal Deadline Approaching",
                message=f'Strategic goal "{goal.title}" target date is {goal.deadline} ({days_left} days remaining).',
                dedup_key=dedup_key,
                source_type='goal',
                source_id=goal.pk
            )
            if created:
                count_created += 1

    # 2. Arcs
    active_arcs = Arc.objects.filter(
        status__in=['ACTIVE', 'PAUSED']
    ).select_related('user', 'user__profile')

    for arc in active_arcs:
        user = arc.user
        local_date = _get_user_local_date(user)
        days_left = (arc.end_date - local_date).days

        if 0 <= days_left <= 7:
            dedup_key = f"arc_deadline_{arc.pk}_{arc.end_date}"
            n, created = create_notification(
                user=user,
                notification_type=Notification.TYPE_ARC_DEADLINE,
                title="Season Ending Soon",
                message=f'Winter Arc "{arc.name}" concludes on {arc.end_date}. Finish strong.',
                dedup_key=dedup_key,
                source_type='arc',
                source_id=arc.pk
            )
            if created:
                count_created += 1

    logger.info(f"process_deadline_notifications complete. Created {count_created} notifications.")
    return count_created


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_streak_notifications(self):
    """
    Check for habit streak milestones (e.g. 7-day, 30-day).
    Uses existing Habit model get_current_streak() service.
    """
    logger.info("Executing process_streak_notifications...")
    count_created = 0

    active_habits = Habit.objects.filter(is_archived=False).select_related('user')
    for habit in active_habits:
        streak = habit.get_current_streak()
        if streak in (7, 30):
            dedup_key = f"streak_milestone_{habit.pk}_{streak}"
            n, created = create_notification(
                user=habit.user,
                notification_type=Notification.TYPE_STREAK_MILESTONE,
                title="Streak Milestone Reached",
                message=f'Incredible discipline! "{habit.name}" has reached an unbroken {streak}-day streak.',
                dedup_key=dedup_key,
                source_type='habit',
                source_id=habit.pk
            )
            if created:
                count_created += 1

    logger.info(f"process_streak_notifications complete. Created {count_created} notifications.")
    return count_created
