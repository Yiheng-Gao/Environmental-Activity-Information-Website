from django import forms
from .models import Activity
from .models import Media, ContactMessage, Profile, Rating
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['category', 'title', 'description', 'location', 'date']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }


class MediaForm(forms.ModelForm):
    file = forms.FileField(
        label="",
        help_text="Click to upload or drag and drop",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,video/*',
            'id': 'media-upload-input'
        })
    )
    
    class Meta:
        model = Media
        fields = ['file']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store description as a custom attribute
        self.upload_description = "Images or Videos (PNG, JPG, MP4, etc.)"


class CustomSignupForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Required.")
    is_organizer = forms.BooleanField(required=False, label="I am an organizer")
    organization_name = forms.CharField(
        max_length=200, 
        required=False, 
        label="Organization Name",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_organizer = cleaned_data.get('is_organizer')
        organization_name = cleaned_data.get('organization_name')
        
        if is_organizer and not organization_name:
            raise forms.ValidationError("Organization name is required when registering as an organizer.")
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            profile, created = Profile.objects.get_or_create(user=user)
            profile.is_organizer = self.cleaned_data.get('is_organizer', False)
            profile.organization_name = self.cleaned_data.get('organization_name', '')
            profile.save()
        return user


class ContactMessageForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        }


class RatingForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=Rating.RATING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=False,
        label="Rating"
    )
    comment = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Share your thoughts about this event'
        }),
        label="Comment"
    )
    
    class Meta:
        model = Rating
        fields = ['rating', 'comment']