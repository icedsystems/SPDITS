from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_email', 'user_role', 'action', 'module',
            'record_id', 'description', 'old_values', 'new_values',
            'ip_address', 'session_id', 'timestamp',
        ]
        read_only_fields = fields
