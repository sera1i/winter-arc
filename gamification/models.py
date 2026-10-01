from django.db import models
from django.conf import settings

class Achievement(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    xp_reward = models.IntegerField(default=0)
    criteria_version = models.IntegerField(default=1)

    def __str__(self):
        return self.name

class UserAchievement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'achievement')

    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"

class XPEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='xp_events')
    source_type = models.CharField(max_length=50, help_text="e.g., 'task', 'habit', 'journal'")
    source_id = models.CharField(max_length=255, help_text="ID of the related object for idempotency")
    amount = models.IntegerField()
    description = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'source_type', 'source_id')

    def __str__(self):
        return f"+{self.amount} XP for {self.user.username} ({self.source_type})"
