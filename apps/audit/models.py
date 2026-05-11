from django.db import models
from django.contrib.postgres.indexes import BrinIndex


class AuditLog(models.Model):
    user = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audit_logs'
    )
    user_email = models.EmailField(blank=True)
    user_role = models.CharField(max_length=50, blank=True)
    action = models.CharField(max_length=100, db_index=True)
    module = models.CharField(max_length=100, blank=True, db_index=True)
    record_id = models.BigIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_id = models.CharField(max_length=40, blank=True)
    extra_data = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['module', 'record_id']),
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        return f"[{self.timestamp}] {self.user_email} — {self.action}"

    class Manager(models.Manager):
        def get_queryset(self):
            return super().get_queryset()

    # Immutable — never allow updates via ORM
    def save(self, *args, **kwargs):
        if self.pk:
            return  # Prevent modification of existing records
        super().save(*args, **kwargs)
