from django.contrib import admin
from .models import UploadBatch


@admin.register(UploadBatch)
class UploadBatchAdmin(admin.ModelAdmin):
    list_display = ['batch_id', 'partner', 'original_filename', 'status', 'total_records', 'source', 'created_at']
    list_filter = ['status', 'source', 'partner']
    search_fields = ['batch_id', 'original_filename']
    readonly_fields = ['batch_id', 'checksum_md5', 'celery_task_id', 'created_at', 'updated_at']
