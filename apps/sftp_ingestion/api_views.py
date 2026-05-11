from rest_framework import generics, permissions
from .models import SFTPIngestionLog
from .serializers import SFTPIngestionLogSerializer


class SFTPLogListAPIView(generics.ListAPIView):
    serializer_class = SFTPIngestionLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SFTPIngestionLog.objects.select_related('partner').order_by('-detected_at')
