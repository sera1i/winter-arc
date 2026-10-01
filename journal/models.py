from django.db import models
from django.conf import settings

class JournalEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='journal_entries')
    local_date = models.DateField(help_text="User's local calendar date")
    
    mood = models.IntegerField(null=True, blank=True, help_text="1 to 5 or similar scale")
    energy = models.IntegerField(null=True, blank=True, help_text="1 to 5 scale")
    sleep_hours = models.FloatField(null=True, blank=True)
    
    reflection = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'local_date')
        verbose_name_plural = "Journal Entries"

    def __str__(self):
        return f"Journal for {self.user.username} on {self.local_date}"
