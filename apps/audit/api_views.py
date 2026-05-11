from rest_framework import generics, permissions
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListAPIView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if not (self.request.user.is_admin() or self.request.user.is_compliance_officer()):
            return AuditLog.objects.none()
        return AuditLog.objects.select_related('user').order_by('-timestamp')[:500]


class AuditFeedAPIView(generics.ListAPIView):
    """Real-time activity feed — last 20 actions."""
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if not (self.request.user.is_admin() or self.request.user.is_compliance_officer()):
            return AuditLog.objects.none()
        return AuditLog.objects.select_related('user').order_by('-timestamp')[:20]
