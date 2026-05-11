from rest_framework import serializers
from .models import UploadBatch


class UploadBatchSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='partner.name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = UploadBatch
        fields = [
            'id', 'batch_id', 'partner', 'partner_name', 'uploaded_by', 'uploaded_by_name',
            'original_filename', 'file_size', 'file_type', 'status', 'status_display',
            'source', 'total_records', 'valid_records', 'invalid_records', 'duplicate_records',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['batch_id', 'created_at', 'updated_at']
