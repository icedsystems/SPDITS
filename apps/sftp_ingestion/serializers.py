from rest_framework import serializers
from .models import SFTPIngestionLog


class SFTPIngestionLogSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='partner.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = SFTPIngestionLog
        fields = [
            'id', 'partner', 'partner_name', 'filename', 'remote_path',
            'file_size', 'checksum_md5', 'status', 'status_display',
            'error_message', 'detected_at', 'processed_at',
        ]
