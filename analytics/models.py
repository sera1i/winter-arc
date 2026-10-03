from django.db import models
from django.conf import settings
from arcs.models import Arc

class ActivityEvent(models.Model):
    EVENT_TASK_CREATED = 'TASK_CREATED'
    EVENT_TASK_COMPLETED = 'TASK_COMPLETED'
    EVENT_GOAL_CREATED = 'GOAL_CREATED'
    EVENT_GOAL_COMPLETED = 'GOAL_COMPLETED'
    EVENT_MILESTONE_COMPLETED = 'MILESTONE_COMPLETED'
    EVENT_HABIT_CREATED = 'HABIT_CREATED'
    EVENT_HABIT_COMPLETED = 'HABIT_COMPLETED'
    EVENT_JOURNAL_CREATED = 'JOURNAL_CREATED'
    EVENT_ARC_STARTED = 'ARC_STARTED'
    EVENT_ARC_COMPLETED = 'ARC_COMPLETED'

    EVENT_TYPE_CHOICES = [
        (EVENT_TASK_CREATED, 'Task Created'),
        (EVENT_TASK_COMPLETED, 'Task Completed'),
        (EVENT_GOAL_CREATED, 'Goal Created'),
        (EVENT_GOAL_COMPLETED, 'Goal Completed'),
        (EVENT_MILESTONE_COMPLETED, 'Milestone Completed'),
        (EVENT_HABIT_CREATED, 'Habit Created'),
        (EVENT_HABIT_COMPLETED, 'Habit Completed'),
        (EVENT_JOURNAL_CREATED, 'Journal Check-in'),
        (EVENT_ARC_STARTED, 'Arc Started'),
        (EVENT_ARC_COMPLETED, 'Arc Completed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activity_events'
    )
    arc = models.ForeignKey(
        Arc,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_events'
    )
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    source_type = models.CharField(max_length=50, blank=True)
    source_id = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'event_type']),
            models.Index(fields=['user', 'arc']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.event_type}: {self.title}"
