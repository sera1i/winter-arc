from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class Arc(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ACTIVE', 'Active'),
        ('PAUSED', 'Paused'),
        ('COMPLETED', 'Completed'),
        ('ARCHIVED', 'Archived'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='arcs')
    name = models.CharField(max_length=255)
    objective = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    is_primary = models.BooleanField(default=False)
    timezone = models.CharField(max_length=50, default='UTC')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError('Start date cannot be after end date.')
        
        # Ensure only one primary active arc
        if self.is_primary:
            primary_arcs = Arc.objects.filter(user=self.user, is_primary=True).exclude(pk=self.pk)
            if primary_arcs.exists():
                raise ValidationError('User can have at most one primary active Arc.')

    def __str__(self):
        return f"{self.name} ({self.user.username})"

