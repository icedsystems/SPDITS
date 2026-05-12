from django.db import models
from apps.accounts.models import CustomUser
from apps.participants.models import get_fernet


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


class EmailConfig(models.Model):
    """Singleton model storing Microsoft Graph API email credentials."""
    tenant_id = models.CharField(max_length=255, blank=True)
    client_id = models.CharField(max_length=255, blank=True)
    _client_secret = models.BinaryField(null=True, blank=True, db_column='client_secret')
    sender_email = models.EmailField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Email Configuration'

    def __str__(self):
        return f'Email Config (sender: {self.sender_email or "not set"})'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def set_secret(self, plaintext):
        if plaintext:
            f = get_fernet()
            self._client_secret = f.encrypt(plaintext.encode())

    def get_secret(self):
        if not self._client_secret:
            return ''
        try:
            f = get_fernet()
            return f.decrypt(bytes(self._client_secret)).decode()
        except Exception:
            return ''

    @property
    def is_configured(self):
        return bool(self.tenant_id and self.client_id and self._client_secret and self.sender_email)

    @property
    def has_secret(self):
        return bool(self._client_secret)
