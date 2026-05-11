from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

from apps.participants.models import Participant, ReIdentificationLog, ParticipantStatus
from apps.uploads.models import UploadBatch


class ComplianceDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'compliance/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        ctx['reidentification_logs'] = ReIdentificationLog.objects.select_related(
            'participant', 'requested_by'
        ).order_by('-viewed_at')[:20]
        ctx['reidentification_count_week'] = ReIdentificationLog.objects.filter(
            viewed_at__gte=week_ago
        ).count()
        ctx['participant_status_counts'] = Participant.objects.values('status').annotate(count=Count('id'))
        ctx['recent_batches'] = UploadBatch.objects.select_related('partner').order_by('-created_at')[:10]
        return ctx
