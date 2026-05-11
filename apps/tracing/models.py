from django.db import models
from apps.accounts.models import CustomUser
from apps.participants.models import Participant


class TracingLog(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='tracing_logs')
    updated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='tracing_updates')
    previous_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30)
    notes = models.TextField(blank=True)
    contact_attempted = models.BooleanField(default=False)
    contact_method = models.CharField(
        max_length=50, blank=True,
        choices=[('phone', 'Phone'), ('visit', 'Physical Visit'), ('sms', 'SMS'), ('email', 'Email'), ('other', 'Other')]
    )
    location_found = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.participant.pseudo_code}: {self.previous_status} → {self.new_status}"
