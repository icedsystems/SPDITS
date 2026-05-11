from rest_framework import serializers
from .models import Interview, InterviewStatusHistory


class InterviewSerializer(serializers.ModelSerializer):
    enumerator_name = serializers.CharField(source='enumerator.get_full_name', read_only=True)
    participant_code = serializers.CharField(source='participant.pseudo_code', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Interview
        fields = [
            'id', 'participant', 'participant_code', 'enumerator', 'enumerator_name',
            'status', 'status_display', 'scheduled_date', 'started_at', 'completed_at',
            'callback_date', 'remarks', 'refusal_reason', 'created_at',
        ]
