import secrets
import hashlib
from django.db import models
from django.utils import timezone
from django.conf import settings
from apps.accounts.models import CustomUser, Partner


class InvitationStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    ACCEPTED = 'accepted', 'Accepted'
    EXPIRED = 'expired', 'Expired'
    REVOKED = 'revoked', 'Revoked'


class Invitation(models.Model):
    email = models.EmailField()
    organization = models.CharField(max_length=255, blank=True)
    partner = models.ForeignKey(Partner, on_delete=models.SET_NULL, null=True, blank=True, related_name='invitations')
    role = models.CharField(max_length=50, choices=CustomUser.role.field.choices)
    invited_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='sent_invitations')
    token = models.CharField(max_length=128, unique=True, editable=False)
    token_hash = models.CharField(max_length=128, editable=False, db_index=True)
    status = models.CharField(max_length=20, choices=InvitationStatus.choices, default=InvitationStatus.PENDING)
    expiry_time = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='accepted_invitation'
    )
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invitation to {self.email} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(64)
            self.token_hash = hashlib.sha256(self.token.encode()).hexdigest()
        if not self.expiry_time:
            from datetime import timedelta
            self.expiry_time = timezone.now() + timedelta(minutes=settings.INVITATION_EXPIRY_MINUTES)
        super().save(*args, **kwargs)

    def is_valid(self):
        return self.status == InvitationStatus.PENDING and timezone.now() < self.expiry_time

    def mark_expired(self):
        self.status = InvitationStatus.EXPIRED
        self.save(update_fields=['status'])

    def mark_accepted(self, user):
        self.status = InvitationStatus.ACCEPTED
        self.accepted_at = timezone.now()
        self.accepted_by = user
        self.save(update_fields=['status', 'accepted_at', 'accepted_by'])

    @property
    def get_accept_url(self):
        return f"{settings.APP_URL}/invitations/accept/{self.token}/"

    @property
    def is_expired(self):
        return timezone.now() >= self.expiry_time
