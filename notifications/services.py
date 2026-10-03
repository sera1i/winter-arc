import logging
from django.db import transaction, IntegrityError
from django.utils import timezone
from .models import Notification, NotificationPreference

logger = logging.getLogger(__name__)

# Mapping from notification type to preference attribute
PREFERENCE_FIELD_MAP = {
    Notification.TYPE_TASK_DUE_SOON: 'task_reminders_enabled',
    Notification.TYPE_TASK_OVERDUE: 'task_reminders_enabled',
    Notification.TYPE_HABIT_REMINDER: 'habit_reminders_enabled',
    Notification.TYPE_STREAK_MILESTONE: 'habit_reminders_enabled',
    Notification.TYPE_GOAL_DEADLINE: 'deadline_reminders_enabled',
    Notification.TYPE_ARC_DEADLINE: 'deadline_reminders_enabled',
    Notification.TYPE_RANK_ACHIEVED: 'gamification_alerts_enabled',
    Notification.TYPE_ACHIEVEMENT_UNLOCKED: 'gamification_alerts_enabled',
}

def get_or_create_user_preferences(user):
    """Ensure user has a NotificationPreference record and return it."""
    prefs, _ = NotificationPreference.objects.get_or_create(user=user)
    return prefs

def is_notification_type_enabled(user, notification_type):
    """Check if the user's preferences permit this notification type."""
    prefs = get_or_create_user_preferences(user)
    field_name = PREFERENCE_FIELD_MAP.get(notification_type)
    if field_name:
        return getattr(prefs, field_name, True)
    return True

def create_notification(
    user,
    notification_type,
    title,
    message,
    dedup_key,
    source_type='',
    source_id='',
    scheduled_for=None,
    force=False
):
    """
    Centralized, transaction-safe, deterministic, and idempotent notification creation.
    
    Parameters:
      - user: Target CustomUser instance
      - notification_type: Type from Notification.TYPE_*
      - title: Short notification title
      - message: Explanatory message content
      - dedup_key: Deterministic unique key (e.g., 'task_due_15_2026-10-04')
      - source_type: Entity domain ('task', 'habit', etc.)
      - source_id: Primary key or identifier
      - scheduled_for: Optional timezone-aware datetime for the event/deadline
      - force: If True, bypasses preference check (useful for system-critical alerts)

    Returns:
      (Notification instance, created: bool)
      Returns (None, False) if suppressed by user preference.
    """
    if not force and not is_notification_type_enabled(user, notification_type):
        logger.info(f"Notification suppressed for {user.username} due to preferences: {notification_type}")
        return None, False

    try:
        with transaction.atomic():
            notification, created = Notification.objects.get_or_create(
                dedup_key=dedup_key,
                defaults={
                    'user': user,
                    'notification_type': notification_type,
                    'title': title,
                    'message': message,
                    'source_type': source_type,
                    'source_id': str(source_id) if source_id else '',
                    'scheduled_for': scheduled_for,
                }
            )
            return notification, created
    except IntegrityError:
        # Concurrent creation race condition safety
        notification = Notification.objects.filter(dedup_key=dedup_key).first()
        return notification, False

def get_unread_count(user):
    """Return count of unread notifications for authenticated user."""
    return Notification.objects.filter(user=user, is_read=False).count()

def mark_notification_as_read(user, notification_id):
    """Mark a specific notification as read, ensuring strict user ownership."""
    notification = Notification.objects.filter(user=user, pk=notification_id).first()
    if notification and not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at'])
        return True
    return False

def mark_all_notifications_as_read(user):
    """Mark all unread notifications as read for user."""
    now = timezone.now()
    return Notification.objects.filter(user=user, is_read=False).update(
        is_read=True,
        read_at=now
    )
