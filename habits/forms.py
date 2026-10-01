from django import forms
from django.utils import timezone
from .models import Habit


class HabitForm(forms.ModelForm):
    class Meta:
        model = Habit
        fields = ['name', 'description', 'frequency', 'active_from', 'active_until']
        widgets = {
            'active_from': forms.DateInput(attrs={'type': 'date'}),
            'active_until': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default active_from to today
        if not self.instance.pk:
            self.initial.setdefault('active_from', timezone.now().date().isoformat())
        self.fields['active_until'].required = False
