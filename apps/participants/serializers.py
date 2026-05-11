from rest_framework import serializers
from .models import Participant


class ParticipantSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='partner.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Participant
        fields = [
            'id', 'pseudo_code', 'partner', 'partner_name', 'upload_batch',
            'status', 'status_display', 'data', 'is_duplicate', 'is_valid',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['pseudo_code', 'created_at', 'updated_at']
