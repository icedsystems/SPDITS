import logging
import csv
from io import StringIO, BytesIO
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView

from apps.accounts.models import CustomUser, Role
from apps.audit.utils import log_action
from apps.participants.models import Participant, ParticipantStatus
from .models import Assignment, AssignmentStatus

logger = logging.getLogger(__name__)


class AssignmentQueueView(LoginRequiredMixin, ListView):
    """Traced participants available for assignment."""
    model = Participant
    template_name = 'assignments/assignment_queue.html'
    context_object_name = 'participants'
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user
        if not (user.is_admin() or user.is_supervisor()):
            return Participant.objects.none()
        return Participant.objects.filter(status=ParticipantStatus.TRACED).select_related('partner')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_supervisor():
            ctx['enumerators'] = CustomUser.objects.filter(role=Role.ENUMERATOR, supervisor=user, is_active=True)
        else:
            ctx['enumerators'] = CustomUser.objects.filter(role=Role.ENUMERATOR, is_active=True)
        return ctx


class BulkAssignView(LoginRequiredMixin, View):
    def post(self, request):
        if not (request.user.is_admin() or request.user.is_supervisor()):
            messages.error(request, 'Permission denied.')
            return redirect('assignments:queue')
        participant_ids = request.POST.getlist('participant_ids')
        enumerator_id = request.POST.get('enumerator_id')
        notes = request.POST.get('notes', '')
        if not participant_ids or not enumerator_id:
            messages.error(request, 'Select participants and an enumerator.')
            return redirect('assignments:queue')
        enumerator = get_object_or_404(CustomUser, pk=enumerator_id, role=Role.ENUMERATOR)
        if request.user.is_supervisor() and enumerator.supervisor != request.user:
            messages.error(request, 'You can only assign to your own enumerators.')
            return redirect('assignments:queue')
        assigned_count = 0
        for pid in participant_ids:
            try:
                p = Participant.objects.get(pk=pid, status=ParticipantStatus.TRACED)
                Assignment.objects.create(
                    participant=p, enumerator=enumerator,
                    supervisor=request.user if request.user.is_supervisor() else enumerator.supervisor,
                    notes=notes
                )
                p.status = ParticipantStatus.ASSIGNED
                p.save(update_fields=['status'])
                assigned_count += 1
            except (Participant.DoesNotExist, Exception) as e:
                logger.warning(f'Assignment error for participant {pid}: {e}')
        log_action(request, 'BULK_ASSIGN', 'assignments',
                   description=f'Assigned {assigned_count} participants to {enumerator.get_full_name()}')
        messages.success(request, f'{assigned_count} participants assigned to {enumerator.get_full_name()}.')
        return redirect('assignments:queue')


class MyAssignmentsView(LoginRequiredMixin, ListView):
    """Enumerator's personal assignment list."""
    model = Assignment
    template_name = 'assignments/my_assignments.html'
    context_object_name = 'assignments'
    paginate_by = 25

    def get_queryset(self):
        return Assignment.objects.filter(
            enumerator=self.request.user, status=AssignmentStatus.ACTIVE
        ).select_related('participant', 'participant__partner')


class AssignmentListView(LoginRequiredMixin, ListView):
    model = Assignment
    template_name = 'assignments/assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user
        qs = Assignment.objects.select_related('participant', 'enumerator', 'supervisor')
        if user.is_enumerator():
            qs = qs.filter(enumerator=user)
        elif user.is_supervisor():
            qs = qs.filter(supervisor=user)
        return qs


class AssignmentExportView(LoginRequiredMixin, View):
    def get(self, request, enumerator_pk):
        enumerator = get_object_or_404(CustomUser, pk=enumerator_pk, role=Role.ENUMERATOR)
        if not (request.user.is_admin() or request.user.is_supervisor()):
            messages.error(request, 'Permission denied.')
            return redirect('assignments:list')
        assignments = Assignment.objects.filter(
            enumerator=enumerator, status=AssignmentStatus.ACTIVE
        ).select_related('participant', 'participant__partner')
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Pseudocode', 'Partner', 'County', 'Gender', 'Age',
            'Phone', 'Tracing Notes', 'Assignment Date'
        ])
        for a in assignments:
            p = a.participant
            d = p.data
            writer.writerow([
                p.pseudo_code, p.partner.name,
                d.get('county', ''), d.get('gender', ''), d.get('age', ''),
                d.get('phone', ''),
                '', a.assigned_at.strftime('%Y-%m-%d'),
            ])
        log_action(request, 'EXPORT_ASSIGNMENTS', 'assignments',
                   description=f'Exported assignments for {enumerator.get_full_name()}')
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="assignments_{enumerator.username}.csv"'
        return response
