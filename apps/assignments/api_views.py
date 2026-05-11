from rest_framework import generics, permissions
from .models import Assignment
from .serializers import AssignmentSerializer


class AssignmentListAPIView(generics.ListAPIView):
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Assignment.objects.select_related('participant', 'enumerator', 'supervisor')
        if user.is_enumerator():
            return qs.filter(enumerator=user)
        elif user.is_supervisor():
            return qs.filter(supervisor=user)
        return qs
