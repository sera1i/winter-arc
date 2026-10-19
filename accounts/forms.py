from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Profile

class CustomUserCreationForm(UserCreationForm):
    display_name = forms.CharField(
        max_length=255,
        required=False,
        label="Display Name",
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. Knight of the North',
            'autocomplete': 'nickname'
        }),
        help_text="Optional public moniker shown on your dashboard and rankings."
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'display_name', 'email')

    def save(self, commit=True):
        user = super().save(commit=commit)
        display_name = self.cleaned_data.get('display_name', '').strip()
        if commit:
            profile, _ = Profile.objects.get_or_create(user=user)
            if display_name:
                profile.display_name = display_name
                profile.save(update_fields=['display_name'])
        return user

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['display_name', 'avatar', 'timezone', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
        }
