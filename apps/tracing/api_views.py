from rest_framework import generics, permissions
from .models import TracingLog
from .serializers import TracingLogSerializer


class TracingLogListAPIView(generics.ListAPIView):
    queryset = TracingLog.objects.select_related('participant', 'updated_by')
    serializer_class = TracingLogSerializer
    permission_classes = [permissions.IsAuthenticated]


class ParticipantTracingLogAPIView(generics.ListAPIView):
    serializer_class = TracingLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TracingLog.objects.filter(participant_id=self.kwargs['participant_pk'])
