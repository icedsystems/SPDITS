from rest_framework import generics, permissions
from .models import Participant
from .serializers import ParticipantSerializer


class ParticipantListAPIView(generics.ListAPIView):
    serializer_class = ParticipantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Participant.objects.select_related('partner')
        if self.request.user.is_partner() and self.request.user.partner:
            qs = qs.filter(partner=self.request.user.partner)
        return qs


class ParticipantDetailAPIView(generics.RetrieveAPIView):
    queryset = Participant.objects.all()
    serializer_class = ParticipantSerializer
    permission_classes = [permissions.IsAuthenticated]
