from django.db import models
from django.utils import timezone
from apps.accounts.models import CustomUser
from apps.participants.models import Participant
from apps.assignments.models import Assignment


class InterviewStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    ASSIGNED = 'assigned', 'Assigned'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    REFUSED = 'refused', 'Refused'
    UNREACHABLE = 'unreachable', 'Unreachable'
    CALLBACK_REQUIRED = 'callback_required', 'Callback Required'


class Interview(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='interviews')
    assignment = models.OneToOneField(Assignment, on_delete=models.SET_NULL, null=True, blank=True, related_name='interview')
    enumerator = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='interviews')
    status = models.CharField(max_length=30, choices=InterviewStatus.choices, default=InterviewStatus.PENDING)
    scheduled_date = models.DateField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    callback_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    refusal_reason = models.TextField(blank=True)
    interview_data = models.JSONField(default=dict, help_text='Collected interview responses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Interview: {self.participant.pseudo_code} ({self.status})"

    def get_status_badge(self):
        colors = {
            InterviewStatus.PENDING: 'secondary',
            InterviewStatus.ASSIGNED: 'primary',
            InterviewStatus.IN_PROGRESS: 'warning',
            InterviewStatus.COMPLETED: 'success',
            InterviewStatus.REFUSED: 'danger',
            InterviewStatus.UNREACHABLE: 'dark',
            InterviewStatus.CALLBACK_REQUIRED: 'info',
        }
        return colors.get(self.status, 'secondary')


class InterviewStatusHistory(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='status_history')
    changed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    previous_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30)
    notes = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']
