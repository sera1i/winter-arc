from django import forms
from .models import NotificationPreference

class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        fields = [
            'task_reminders_enabled',
            'habit_reminders_enabled',
            'deadline_reminders_enabled',
            'gamification_alerts_enabled',
            'quiet_start',
            'quiet_end',
        ]
        widgets = {
            'quiet_start': forms.TimeInput(attrs={'type': 'time', 'class': 'wa-input w-full font-mono text-sm'}),
            'quiet_end': forms.TimeInput(attrs={'type': 'time', 'class': 'wa-input w-full font-mono text-sm'}),
        }
