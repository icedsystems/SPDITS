from rest_framework import serializers
from .models import TracingLog


class TracingLogSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)

    class Meta:
        model = TracingLog
        fields = [
            'id', 'participant', 'updated_by', 'updated_by_name',
            'previous_status', 'new_status', 'notes',
            'contact_attempted', 'contact_method', 'location_found', 'created_at',
        ]
