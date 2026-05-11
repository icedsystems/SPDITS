from rest_framework import generics, permissions
from .models import UploadBatch
from .serializers import UploadBatchSerializer


class UploadBatchListAPIView(generics.ListAPIView):
    serializer_class = UploadBatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = UploadBatch.objects.select_related('partner', 'uploaded_by')
        if self.request.user.is_partner() and self.request.user.partner:
            qs = qs.filter(partner=self.request.user.partner)
        return qs


class UploadBatchDetailAPIView(generics.RetrieveAPIView):
    queryset = UploadBatch.objects.all()
    serializer_class = UploadBatchSerializer
    permission_classes = [permissions.IsAuthenticated]
