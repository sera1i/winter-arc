from django.db import models
from django.conf import settings

class AuditEvent(models.Model):
    actor_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50)
    entity_type = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        actor = self.actor_user.username if self.actor_user else 'System'
        return f"{actor} {self.action} {self.entity_type} {self.entity_id}"
