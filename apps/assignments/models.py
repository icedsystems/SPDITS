import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import CustomUser
from apps.participants.models import Participant


class AssignmentStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    REASSIGNED = 'reassigned', 'Reassigned'
    COMPLETED = 'completed', 'Completed'


class Assignment(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='assignments')
    enumerator = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='assignments',
        limit_choices_to={'role': 'enumerator'}
    )
    supervisor = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, related_name='supervised_assignments',
        limit_choices_to={'role': 'supervisor'}
    )
    status = models.CharField(max_length=20, choices=AssignmentStatus.choices, default=AssignmentStatus.ACTIVE)
    notes = models.TextField(blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-assigned_at']
        unique_together = [['participant', 'enumerator', 'status']]

    def __str__(self):
        return f"{self.participant.pseudo_code} → {self.enumerator.get_full_name()}"


def _token_expiry():
    return timezone.now() + timedelta(minutes=30)


class AssignmentExportToken(models.Model):
    """Secure, time-limited download token for assignment CSV with full identity data."""
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    enumerator = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='export_tokens'
    )
    assigned_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, related_name='issued_export_tokens'
    )
    participant_count = models.PositiveIntegerField(default=0)
    csv_data = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=_token_expiry)
    downloaded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def is_valid(self):
        return timezone.now() < self.expires_at

    def __str__(self):
        return f"Export token for {self.enumerator.get_full_name()} ({self.participant_count} participants)"
