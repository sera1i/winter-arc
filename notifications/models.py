from django.db import models
from django.conf import settings

class NotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preference')
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=False)
    quiet_start = models.TimeField(null=True, blank=True, help_text="Start of quiet hours (local time)")
    quiet_end = models.TimeField(null=True, blank=True, help_text="End of quiet hours (local time)")

    # Channel-specific and domain-specific preference controls
    task_reminders_enabled = models.BooleanField(default=True, help_text="Receive task due soon & overdue alerts")
    habit_reminders_enabled = models.BooleanField(default=True, help_text="Receive daily habit check-in reminders")
    deadline_reminders_enabled = models.BooleanField(default=True, help_text="Receive goal and Arc deadline notices")
    gamification_alerts_enabled = models.BooleanField(default=True, help_text="Receive rank promotions and badge unlocks")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Prefs for {self.user.username}"


class Notification(models.Model):
    TYPE_TASK_DUE_SOON = 'TASK_DUE_SOON'
    TYPE_TASK_OVERDUE = 'TASK_OVERDUE'
    TYPE_HABIT_REMINDER = 'HABIT_REMINDER'
    TYPE_STREAK_MILESTONE = 'STREAK_MILESTONE'
    TYPE_GOAL_DEADLINE = 'GOAL_DEADLINE'
    TYPE_ARC_DEADLINE = 'ARC_DEADLINE'
    TYPE_RANK_ACHIEVED = 'RANK_ACHIEVED'
    TYPE_ACHIEVEMENT_UNLOCKED = 'ACHIEVEMENT_UNLOCKED'

    NOTIFICATION_TYPE_CHOICES = [
        (TYPE_TASK_DUE_SOON, 'Task Due Soon'),
        (TYPE_TASK_OVERDUE, 'Task Overdue'),
        (TYPE_HABIT_REMINDER, 'Habit Reminder'),
        (TYPE_STREAK_MILESTONE, 'Streak Milestone'),
        (TYPE_GOAL_DEADLINE, 'Goal Deadline'),
        (TYPE_ARC_DEADLINE, 'Arc Deadline'),
        (TYPE_RANK_ACHIEVED, 'Rank Achieved'),
        (TYPE_ACHIEVEMENT_UNLOCKED, 'Achievement Unlocked'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    # Optional references
    source_type = models.CharField(max_length=50, blank=True, help_text="e.g. task, habit, goal, arc, rank, achievement")
    source_id = models.CharField(max_length=255, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)

    # Deduplication key for database uniqueness constraint
    dedup_key = models.CharField(max_length=255, unique=True, help_text="Unique key ensuring strict idempotency")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'notification_type']),
        ]

    def __str__(self):
        return f"{self.user.username} - [{self.notification_type}] {self.title}"


class NotificationJob(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=50) # e.g. 'TASK_REMINDER'
    scheduled_for = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    attempts = models.IntegerField(default=0)
    
    reference_id = models.CharField(max_length=255, blank=True, help_text="For idempotency")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.notification_type} for {self.user.username} at {self.scheduled_for}"
