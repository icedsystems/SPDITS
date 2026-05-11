from django.db import models
from apps.accounts.models import CustomUser


class NotificationType(models.TextChoices):
    INVITATION = 'invitation', 'Invitation'
    UPLOAD_APPROVED = 'upload_approved', 'Upload Approved'
    UPLOAD_REJECTED = 'upload_rejected', 'Upload Rejected'
    NEW_UPLOAD = 'new_upload', 'New Upload'
    ASSIGNMENT = 'assignment', 'New Assignment'
    SUSPICIOUS_ACTIVITY = 'suspicious_activity', 'Suspicious Activity'
    SFTP_ALERT = 'sftp_alert', 'SFTP Alert'
    SYSTEM = 'system', 'System'


class Notification(models.Model):
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.email} — {self.title}"

    def mark_read(self):
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])
