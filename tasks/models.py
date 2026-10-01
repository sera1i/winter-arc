from django.db import models
from django.conf import settings
from django.utils import timezone
from goals.models import Goal


class Task(models.Model):
    PRIORITY_HIGH = 1
    PRIORITY_MEDIUM = 2
    PRIORITY_LOW = 3
    PRIORITY_CHOICES = [
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_LOW, 'Low'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks'
    )
    goal = models.ForeignKey(
        Goal, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks'
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    priority = models.IntegerField(default=PRIORITY_MEDIUM, choices=PRIORITY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    recurrence_rule = models.CharField(
        max_length=255, blank=True, help_text="iCal RRULE string or similar"
    )

    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', 'due_at', '-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'due_at']),
        ]

    @property
    def is_completed(self):
        return self.status == 'COMPLETED'

    @property
    def priority_label(self):
        return dict(self.PRIORITY_CHOICES).get(self.priority, 'Medium')

    def complete(self):
        """Mark this task as completed with a timestamp."""
        self.status = 'COMPLETED'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])

    def uncomplete(self):
        """Revert this task to pending."""
        self.status = 'PENDING'
        self.completed_at = None
        self.save(update_fields=['status', 'completed_at', 'updated_at'])

    def __str__(self):
        return self.title
