from django import forms
from .models import Arc

class ArcForm(forms.ModelForm):
    class Meta:
        model = Arc
        fields = ['name', 'objective', 'start_date', 'end_date', 'status', 'is_primary', 'timezone']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'objective': forms.Textarea(attrs={'rows': 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and start_date > end_date:
            self.add_error('start_date', 'Start date cannot be after end date.')
            self.add_error('end_date', 'End date cannot be before start date.')
            
        return cleaned_data
