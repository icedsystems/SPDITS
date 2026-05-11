from rest_framework import serializers
from .models import Assignment


class AssignmentSerializer(serializers.ModelSerializer):
    enumerator_name = serializers.CharField(source='enumerator.get_full_name', read_only=True)
    supervisor_name = serializers.CharField(source='supervisor.get_full_name', read_only=True)
    participant_code = serializers.CharField(source='participant.pseudo_code', read_only=True)

    class Meta:
        model = Assignment
        fields = [
            'id', 'participant', 'participant_code', 'enumerator', 'enumerator_name',
            'supervisor', 'supervisor_name', 'status', 'notes', 'assigned_at', 'due_date',
        ]
