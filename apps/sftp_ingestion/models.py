from django.db import models
from apps.accounts.models import Partner


class SFTPConfig(models.Model):
    partner = models.OneToOneField(Partner, on_delete=models.CASCADE, related_name='sftp_config')
    username = models.CharField(max_length=100)
    inbound_directory = models.CharField(max_length=500, help_text='Remote path where partner uploads files')
    processing_directory = models.CharField(max_length=500, blank=True)
    archive_directory = models.CharField(max_length=500, blank=True)
    failed_directory = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SFTP Config — {self.partner.name}"


class SFTPIngestionStatus(models.TextChoices):
    DETECTED = 'detected', 'Detected'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    DUPLICATE = 'duplicate', 'Duplicate (Skipped)'


class SFTPIngestionLog(models.Model):
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='sftp_logs')
    filename = models.CharField(max_length=255)
    remote_path = models.CharField(max_length=500)
    local_path = models.CharField(max_length=500, blank=True)
    file_size = models.BigIntegerField(default=0)
    checksum_md5 = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=20, choices=SFTPIngestionStatus.choices, default=SFTPIngestionStatus.DETECTED)
    error_message = models.TextField(blank=True)
    upload_batch = models.ForeignKey(
        'uploads.UploadBatch', on_delete=models.SET_NULL, null=True, blank=True
    )
    detected_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-detected_at']

    def __str__(self):
        return f"{self.filename} — {self.partner.name} ({self.status})"
