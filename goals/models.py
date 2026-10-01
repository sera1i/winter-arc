from django.db import models
from django.conf import settings
from arcs.models import Arc

class Goal(models.Model):
    CATEGORY_CHOICES = [
        ('HEALTH', 'Health & Fitness'),
        ('PRODUCTIVITY', 'Productivity'),
        ('LEARNING', 'Learning'),
        ('FINANCE', 'Finance'),
        ('OTHER', 'Other'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goals')
    arc = models.ForeignKey(Arc, on_delete=models.CASCADE, related_name='goals', null=True, blank=True)
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='OTHER')
    priority = models.IntegerField(default=1) # e.g. 1 High, 2 Medium, 3 Low
    
    target_value = models.FloatField(null=True, blank=True)
    current_value = models.FloatField(default=0)
    unit = models.CharField(max_length=50, blank=True)
    
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @property
    def progress_percentage(self):
        milestones = self.milestones.all()
        if not milestones:
            return 100 if self.status == 'COMPLETED' else 0
        completed = len([m for m in milestones if m.is_completed])
        return int((completed / len(milestones)) * 100)

class Milestone(models.Model):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=255)
    target_value = models.FloatField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_completed(self):
        return self.completed_at is not None

    def __str__(self):
        return f"{self.title} (Goal: {self.goal.title})"
