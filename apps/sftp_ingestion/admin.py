from django.contrib import admin
from .models import SFTPConfig, SFTPIngestionLog


@admin.register(SFTPConfig)
class SFTPConfigAdmin(admin.ModelAdmin):
    list_display = ['partner', 'username', 'inbound_directory', 'is_active']
    list_filter = ['is_active']


@admin.register(SFTPIngestionLog)
class SFTPIngestionLogAdmin(admin.ModelAdmin):
    list_display = ['filename', 'partner', 'status', 'file_size', 'detected_at']
    list_filter = ['status', 'partner']
    search_fields = ['filename', 'remote_path']
    readonly_fields = ['detected_at', 'processed_at', 'checksum_md5']
