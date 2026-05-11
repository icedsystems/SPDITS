from django.db import models
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
