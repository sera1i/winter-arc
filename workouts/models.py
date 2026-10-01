from django.db import models
from django.conf import settings
from goals.models import Goal

class WorkoutSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workout_sessions')
    goal = models.ForeignKey(Goal, on_delete=models.SET_NULL, null=True, blank=True, related_name='workout_sessions')
    
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Workout on {self.started_at}"

class ExerciseRecord(models.Model):
    workout = models.ForeignKey(WorkoutSession, on_delete=models.CASCADE, related_name='exercises')
    exercise_name = models.CharField(max_length=255)
    sets = models.IntegerField(default=1)
    reps = models.IntegerField(null=True, blank=True)
    load = models.FloatField(null=True, blank=True, help_text="Weight or resistance")
    duration = models.IntegerField(null=True, blank=True, help_text="Duration in seconds if applicable")
    
    def __str__(self):
        return f"{self.exercise_name} ({self.sets} sets)"
