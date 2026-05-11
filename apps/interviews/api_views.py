from rest_framework import generics, permissions
from .models import Interview
from .serializers import InterviewSerializer


class InterviewListAPIView(generics.ListAPIView):
    serializer_class = InterviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Interview.objects.select_related('participant', 'enumerator')
        if user.is_enumerator():
            return qs.filter(enumerator=user)
        return qs


class InterviewDetailAPIView(generics.RetrieveUpdateAPIView):
    queryset = Interview.objects.all()
    serializer_class = InterviewSerializer
    permission_classes = [permissions.IsAuthenticated]
