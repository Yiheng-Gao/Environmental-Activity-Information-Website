from django import forms
from .models import Activity
from .models import Media
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['category', 'title', 'description', 'location', 'date']


class MediaForm(forms.ModelForm):
    class Meta:
        model = Media
        fields = ['file']


class CustomSignupForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Required.")

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user