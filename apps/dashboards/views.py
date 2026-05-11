import logging
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.utils import timezone
from datetime import timedelta
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)


class HomeView(LoginRequiredMixin, TemplateView):
    """Route users to their appropriate dashboard."""

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_admin():
            return AdminDashboardView.as_view()(request)
        elif user.is_partner():
            return PartnerDashboardView.as_view()(request)
        elif user.is_supervisor():
            return SupervisorDashboardView.as_view()(request)
        elif user.is_enumerator():
            return EnumeratorDashboardView.as_view()(request)
        elif user.is_compliance_officer():
            return redirect('compliance:dashboard')
        elif user.is_tracer():
            return redirect('tracing:queue')
        return redirect('accounts:login')


class AdminDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboards/admin_dashboard.html'

    def get_context_data(self, **kwargs):
        from apps.uploads.models import UploadBatch, BatchStatus
        from apps.participants.models import Participant, ParticipantStatus
        from apps.interviews.models import Interview, InterviewStatus
        from apps.sftp_ingestion.models import SFTPIngestionLog, SFTPIngestionStatus
        from apps.audit.models import AuditLog

        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        ctx = super().get_context_data(**kwargs)
        ctx['total_uploads'] = UploadBatch.objects.count()
        ctx['pending_approvals'] = UploadBatch.objects.filter(status=BatchStatus.PENDING_APPROVAL).count()
        ctx['total_participants'] = Participant.objects.count()
        ctx['tracing_queue'] = Participant.objects.filter(
            status__in=[ParticipantStatus.UPLOADED, ParticipantStatus.TRACING]
        ).count()
        ctx['traced_queue'] = Participant.objects.filter(status=ParticipantStatus.TRACED).count()
        ctx['active_interviews'] = Interview.objects.filter(
            status__in=[InterviewStatus.ASSIGNED, InterviewStatus.IN_PROGRESS]
        ).count()
        ctx['completed_interviews'] = Interview.objects.filter(status=InterviewStatus.COMPLETED).count()
        ctx['sftp_today'] = SFTPIngestionLog.objects.filter(detected_at__date=today).count()
        ctx['sftp_failed'] = SFTPIngestionLog.objects.filter(
            status=SFTPIngestionStatus.FAILED, detected_at__date__gte=week_ago
        ).count()
        ctx['failed_logins_week'] = AuditLog.objects.filter(
            action='LOGIN_FAILED', timestamp__date__gte=week_ago
        ).count()
        ctx['recent_batches'] = UploadBatch.objects.select_related('partner', 'uploaded_by').order_by('-created_at')[:5]
        ctx['recent_audit'] = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]
        ctx['status_breakdown'] = Participant.objects.values('status').annotate(count=Count('id'))
        return ctx


class PartnerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboards/partner_dashboard.html'

    def get_context_data(self, **kwargs):
        from apps.uploads.models import UploadBatch, BatchStatus
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        if user.partner:
            qs = UploadBatch.objects.filter(partner=user.partner)
            ctx['total_uploads'] = qs.count()
            ctx['pending'] = qs.filter(status=BatchStatus.PENDING_APPROVAL).count()
            ctx['approved'] = qs.filter(status=BatchStatus.APPROVED).count()
            ctx['rejected'] = qs.filter(status=BatchStatus.REJECTED).count()
            ctx['recent_batches'] = qs.order_by('-created_at')[:5]
        return ctx


class SupervisorDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboards/supervisor_dashboard.html'

    def get_context_data(self, **kwargs):
        from apps.accounts.models import CustomUser, Role
        from apps.assignments.models import Assignment, AssignmentStatus
        from apps.interviews.models import Interview, InterviewStatus
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        my_enumerators = CustomUser.objects.filter(role=Role.ENUMERATOR, supervisor=user, is_active=True)
        ctx['enumerator_count'] = my_enumerators.count()
        ctx['active_assignments'] = Assignment.objects.filter(
            supervisor=user, status=AssignmentStatus.ACTIVE
        ).count()
        ctx['completed_interviews'] = Interview.objects.filter(
            enumerator__in=my_enumerators, status=InterviewStatus.COMPLETED
        ).count()
        ctx['pending_interviews'] = Interview.objects.filter(
            enumerator__in=my_enumerators,
            status__in=[InterviewStatus.PENDING, InterviewStatus.ASSIGNED]
        ).count()
        ctx['my_enumerators'] = my_enumerators.annotate(
            assignment_count=Count('assignments'),
        )
        return ctx


class EnumeratorDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboards/enumerator_dashboard.html'

    def get_context_data(self, **kwargs):
        from apps.assignments.models import Assignment, AssignmentStatus
        from apps.interviews.models import Interview, InterviewStatus
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['active_assignments'] = Assignment.objects.filter(
            enumerator=user, status=AssignmentStatus.ACTIVE
        ).count()
        ctx['my_interviews'] = Interview.objects.filter(enumerator=user).order_by('-created_at')[:10]
        ctx['completed'] = Interview.objects.filter(enumerator=user, status=InterviewStatus.COMPLETED).count()
        ctx['pending'] = Interview.objects.filter(
            enumerator=user, status__in=[InterviewStatus.PENDING, InterviewStatus.ASSIGNED]
        ).count()
        return ctx
