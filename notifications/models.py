from django.db import models
from django.conf import settings

class NotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preference')
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=False)
    quiet_start = models.TimeField(null=True, blank=True, help_text="Start of quiet hours (local time)")
    quiet_end = models.TimeField(null=True, blank=True, help_text="End of quiet hours (local time)")

    def __str__(self):
        return f"Prefs for {self.user.username}"

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
