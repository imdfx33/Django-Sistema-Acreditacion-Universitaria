# calendar_create_event/forms.py
from django import forms
from .models import Event
from django.contrib.auth import get_user_model

User = get_user_model()


class EventForm(forms.ModelForm):
    participants = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Participantes"
    )

    class Meta:
        model = Event
        fields = ['title', 'description', 'date', 'time', 'meeting_type', 'location', 'link', 'participants']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
        }
