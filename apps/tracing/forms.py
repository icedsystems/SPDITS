from django import forms
from apps.participants.models import ParticipantStatus


class TracingUpdateForm(forms.Form):
    STATUS_CHOICES = [
        (ParticipantStatus.TRACING, 'Tracing'),
        (ParticipantStatus.TRACED, 'Traced'),
    ]
    new_status = forms.ChoiceField(choices=STATUS_CHOICES)
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    contact_attempted = forms.BooleanField(required=False)
    contact_method = forms.ChoiceField(
        choices=[('', '---'), ('phone', 'Phone'), ('visit', 'Physical Visit'),
                 ('sms', 'SMS'), ('email', 'Email'), ('other', 'Other')],
        required=False
    )
    location_found = forms.CharField(max_length=255, required=False)
