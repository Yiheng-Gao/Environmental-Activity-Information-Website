from django import forms
from .models import Activity
from .models import Media

class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['category', 'title', 'description', 'location', 'date']


class MediaForm(forms.ModelForm):
    class Meta:
        model = Media
        fields = ['file']
