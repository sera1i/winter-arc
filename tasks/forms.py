from django import forms
from .models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'priority', 'status', 'due_at', 'goal']
        widgets = {
            'due_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'
            ),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show the user's own goals in the goal dropdown
        if user is not None:
            from goals.models import Goal
            self.fields['goal'].queryset = Goal.objects.filter(
                user=user, status__in=['PENDING', 'IN_PROGRESS']
            )
        self.fields['goal'].required = False
        self.fields['goal'].empty_label = '— No Goal —'
