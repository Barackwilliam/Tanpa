from django import forms

from .models import EventRegistration


class EventRegistrationForm(forms.ModelForm):
    class Meta:
        model = EventRegistration
        fields = ["full_name", "phone", "institution"]
        labels = {"full_name": "Name as it should appear on your badge", "institution": "Institution / hospital"}
