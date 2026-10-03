from django.db import models
from django.conf import settings
from django.utils import timezone
from zoneinfo import ZoneInfo
from datetime import date, timedelta


class Habit(models.Model):
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('SELECTED_DAYS', 'Selected Days'),
        ('TARGET_COUNT', 'Target Count'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='habits'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, default='DAILY'
    )
    target_count = models.IntegerField(
        default=1, help_text="Used for TARGET_COUNT or times per period"
    )
    active_from = models.DateField()
    active_until = models.DateField(null=True, blank=True)

    is_archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['user', 'is_archived']),
        ]

    def get_user_today(self):
        """Return today's date in the user's configured timezone."""
        try:
            profile = getattr(self.user, 'profile', None)
            tz_name = getattr(profile, 'timezone', None) if profile else None
            if not tz_name:
                tz_name = getattr(settings, 'TIME_ZONE', 'Asia/Kolkata')
            user_tz = ZoneInfo(tz_name)
        except Exception:
            user_tz = timezone.get_current_timezone()
        return timezone.now().astimezone(user_tz).date()

    def is_completed_today(self):
        """Return True if there's a completion record for today (user-local date)."""
        today = self.get_user_today()
        return self.completions.filter(local_date=today).exists()

    def get_current_streak(self):
        """
        Calculate the current consecutive-day completion streak.
        
        Rules:
        - A streak is the number of consecutive days (going backward from today
          or yesterday) that have a completion record.
        - If today is not yet completed, we check from yesterday backward.
          If today IS completed, we check from today backward.
        - A missed day (no completion) breaks the streak immediately.
        - Future dates do NOT count.
        - Only one record per day is needed (enforced by unique_together).
        """
        today = self.get_user_today()
        completed_dates = set(
            self.completions.values_list('local_date', flat=True)
        )
        if not completed_dates:
            return 0

        # Start from today if completed, otherwise from yesterday
        check_date = today if today in completed_dates else today - timedelta(days=1)

        streak = 0
        while check_date in completed_dates:
            streak += 1
            check_date -= timedelta(days=1)

        return streak

    @property
    def best_streak(self):
        """
        Calculate the longest consecutive-day completion streak in this habit's history.
        """
        dates = sorted(set(self.completions.values_list('local_date', flat=True)))
        if not dates:
            return 0

        max_streak = 0
        current = 0
        prev_date = None
        for d in dates:
            if prev_date is None or d == prev_date + timedelta(days=1):
                current += 1
            else:
                current = 1
            if current > max_streak:
                max_streak = current
            prev_date = d

        return max_streak

    def get_completion_history(self, days=30):
        """Return completion records for the last N days, ordered by date desc."""
        today = self.get_user_today()
        since = today - timedelta(days=days - 1)
        return self.completions.filter(local_date__gte=since).order_by('-local_date')

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"


class HabitCompletion(models.Model):
    habit = models.ForeignKey(
        Habit, on_delete=models.CASCADE, related_name='completions'
    )
    local_date = models.DateField(help_text="The user's local date when completed")
    quantity = models.IntegerField(default=1)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('habit', 'local_date')
        ordering = ['-local_date']
        indexes = [
            models.Index(fields=['habit', 'local_date']),
        ]

    def __str__(self):
        return f"{self.habit.name} on {self.local_date}"
