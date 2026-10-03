from django import forms
from .models import Goal, Milestone

class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['title', 'description', 'category', 'priority', 'deadline', 'status']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class MilestoneForm(forms.ModelForm):
    class Meta:
        model = Milestone
        fields = ['title', 'due_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }
