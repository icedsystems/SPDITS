import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views.generic import ListView, DetailView
from django.shortcuts import render

from .models import AuditLog

logger = logging.getLogger(__name__)

SUSPICIOUS_ACTIONS = ['LOGIN_FAILED', 'REIDENTIFY', 'EXPORT_PARTICIPANTS', 'EXPORT_ASSIGNMENTS']


class AuditLogListView(LoginRequiredMixin, ListView):
    model = AuditLog
    template_name = 'audit/audit_list.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        if not (self.request.user.is_admin() or self.request.user.is_compliance_officer()):
            return AuditLog.objects.none()
        qs = AuditLog.objects.select_related('user')
        action = self.request.GET.get('action')
        module = self.request.GET.get('module')
        user_q = self.request.GET.get('user')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        suspicious = self.request.GET.get('suspicious')
        if action:
            qs = qs.filter(action__icontains=action)
        if module:
            qs = qs.filter(module=module)
        if user_q:
            qs = qs.filter(user_email__icontains=user_q)
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)
        if suspicious:
            qs = qs.filter(action__in=SUSPICIOUS_ACTIONS)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['distinct_actions'] = AuditLog.objects.values_list('action', flat=True).distinct().order_by('action')
        ctx['distinct_modules'] = AuditLog.objects.values_list('module', flat=True).distinct().order_by('module')
        ctx['suspicious_count'] = AuditLog.objects.filter(action__in=SUSPICIOUS_ACTIONS).count()
        return ctx


class AuditLogDetailView(LoginRequiredMixin, DetailView):
    model = AuditLog
    template_name = 'audit/audit_detail.html'
    context_object_name = 'log'


class AuditLogExportView(LoginRequiredMixin, ListView):
    def get(self, request):
        if not (request.user.is_admin() or request.user.is_compliance_officer()):
            return HttpResponse('Permission denied', status=403)
        import csv
        from io import StringIO
        from .utils import log_action
        qs = AuditLog.objects.all().order_by('-timestamp')[:10000]
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Timestamp', 'User', 'Role', 'Action', 'Module', 'Record ID', 'Description', 'IP Address', 'Session'])
        for log in qs:
            writer.writerow([
                log.timestamp, log.user_email, log.user_role, log.action,
                log.module, log.record_id, log.description, log.ip_address, log.session_id,
            ])
        log_action(request, 'EXPORT_AUDIT_LOGS', 'audit', description='Exported audit logs')
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
        return response


class UserTimelineView(LoginRequiredMixin, ListView):
    model = AuditLog
    template_name = 'audit/user_timeline.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        if not (self.request.user.is_admin() or self.request.user.is_compliance_officer()):
            return AuditLog.objects.none()
        user_id = self.kwargs.get('user_id')
        return AuditLog.objects.filter(user_id=user_id).order_by('-timestamp')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.accounts.models import CustomUser
        ctx['target_user'] = CustomUser.objects.filter(pk=self.kwargs.get('user_id')).first()
        return ctx


class AuditDashboardView(LoginRequiredMixin, ListView):
    model = AuditLog
    template_name = 'audit/audit_dashboard.html'

    def get(self, request):
        if not (request.user.is_admin() or request.user.is_compliance_officer()):
            from django.shortcuts import redirect
            return redirect('dashboards:home')
        from django.db.models import Count
        from django.utils import timezone
        from datetime import timedelta
        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        ctx = {
            'total_logs': AuditLog.objects.count(),
            'today_logs': AuditLog.objects.filter(timestamp__date=today).count(),
            'failed_logins': AuditLog.objects.filter(action='LOGIN_FAILED', timestamp__date__gte=week_ago).count(),
            'reidentifications': AuditLog.objects.filter(action='REIDENTIFY', timestamp__date__gte=week_ago).count(),
            'suspicious_logs': AuditLog.objects.filter(action__in=SUSPICIOUS_ACTIONS).order_by('-timestamp')[:10],
            'recent_logins': AuditLog.objects.filter(action='LOGIN').order_by('-timestamp')[:10],
            'top_actions': AuditLog.objects.values('action').annotate(count=Count('id')).order_by('-count')[:10],
            'activity_by_module': AuditLog.objects.values('module').annotate(count=Count('id')).order_by('-count'),
        }
        return render(request, self.template_name, ctx)
