import os
from django.db import models
from django.utils import timezone
from apps.accounts.models import CustomUser, Partner


class BatchStatus(models.TextChoices):
    UPLOADED = 'uploaded', 'Uploaded'
    PROCESSING = 'processing', 'Processing'
    PROCESSED = 'processed', 'Processed'
    PENDING_APPROVAL = 'pending_approval', 'Pending Approval'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    FAILED = 'failed', 'Failed'


class UploadBatch(models.Model):
    batch_id = models.CharField(max_length=50, unique=True)
    partner = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name='upload_batches')
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='upload_batches')
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField(default=0)
    file_type = models.CharField(max_length=20)
    status = models.CharField(max_length=30, choices=BatchStatus.choices, default=BatchStatus.UPLOADED)
    source = models.CharField(max_length=20, choices=[('web', 'Web Upload'), ('sftp', 'SFTP')], default='web')

    # Processing summary
    total_records = models.IntegerField(default=0)
    valid_records = models.IntegerField(default=0)
    invalid_records = models.IntegerField(default=0)
    duplicate_records = models.IntegerField(default=0)
    processing_errors = models.JSONField(default=list)
    validation_report = models.JSONField(default=dict)

    # Approval
    reviewed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_batches'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    # Metadata
    checksum_md5 = models.CharField(max_length=32, blank=True)
    is_malware_scanned = models.BooleanField(default=False)
    celery_task_id = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Upload Batch'
        verbose_name_plural = 'Upload Batches'

    def __str__(self):
        return f"{self.batch_id} — {self.partner.name} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.batch_id:
            import uuid
            from datetime import datetime
            self.batch_id = f"BATCH-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def filename(self):
        return os.path.basename(self.file.name) if self.file else self.original_filename

    def get_status_badge(self):
        colors = {
            BatchStatus.UPLOADED: 'secondary',
            BatchStatus.PROCESSING: 'warning',
            BatchStatus.PROCESSED: 'info',
            BatchStatus.PENDING_APPROVAL: 'warning',
            BatchStatus.APPROVED: 'success',
            BatchStatus.REJECTED: 'danger',
            BatchStatus.FAILED: 'danger',
        }
        return colors.get(self.status, 'secondary')

    def approve(self, user, notes=''):
        self.status = BatchStatus.APPROVED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_notes'])

    def reject(self, user, notes=''):
        self.status = BatchStatus.REJECTED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_notes'])
