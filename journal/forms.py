from django import forms
from django.core.exceptions import ValidationError
from .models import JournalEntry

MOOD_CHOICES = [
    ('', '— Select Mood —'),
    (1, '1 — Severely Depleted'),
    (2, '2 — Low / Struggling'),
    (3, '3 — Neutral / Steady'),
    (4, '4 — Strong / Focused'),
    (5, '5 — Unstoppable / Peak'),
]

ENERGY_CHOICES = [
    ('', '— Select Energy —'),
    (1, '1 — Exhausted'),
    (2, '2 — Fatigued'),
    (3, '3 — Moderate'),
    (4, '4 — High'),
    (5, '5 — Overflowing'),
]

class JournalEntryForm(forms.ModelForm):
    mood = forms.ChoiceField(
        choices=MOOD_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'wa-input cursor-pointer appearance-none pr-10'})
    )
    energy = forms.ChoiceField(
        choices=ENERGY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'wa-input cursor-pointer appearance-none pr-10'})
    )

    class Meta:
        model = JournalEntry
        fields = ['local_date', 'mood', 'energy', 'sleep_hours', 'reflection', 'notes']
        widgets = {
            'local_date': forms.DateInput(attrs={'type': 'date', 'class': 'wa-input [color-scheme:dark]'}),
            'sleep_hours': forms.NumberInput(attrs={'step': '0.5', 'min': '0', 'max': '24', 'placeholder': 'e.g. 7.5', 'class': 'wa-input'}),
            'reflection': forms.Textarea(attrs={'rows': 5, 'placeholder': 'What was your primary focus, challenge, and triumph today?', 'class': 'wa-textarea'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tactical notes, observations, or adjustments for tomorrow...', 'class': 'wa-textarea'}),
        }
        labels = {
            'local_date': 'Date',
            'mood': 'Mindset / Mood',
            'energy': 'Energy Level',
            'sleep_hours': 'Sleep (Hours)',
            'reflection': 'Daily Reflection',
            'notes': 'Tactical Notes',
        }
        help_texts = {
            'local_date': 'Calendar date of this entry in your local timezone.',
            'sleep_hours': 'Hours of rest logged last night (optional).',
            'reflection': 'Your candid self-assessment of discipline and focus.',
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_mood(self):
        val = self.cleaned_data.get('mood')
        if val in ('', None):
            return None
        return int(val)

    def clean_energy(self):
        val = self.cleaned_data.get('energy')
        if val in ('', None):
            return None
        return int(val)

    def clean(self):
        cleaned_data = super().clean()
        local_date = cleaned_data.get('local_date')
        if local_date and self.user:
            qs = JournalEntry.objects.filter(user=self.user, local_date=local_date)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('local_date', f'A journal entry already exists for {local_date}. You can edit your existing entry.')
        return cleaned_data
