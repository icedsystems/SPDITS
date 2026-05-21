import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, DetailView

from apps.audit.utils import log_action
from apps.assignments.models import Assignment, AssignmentStatus
from apps.participants.models import Participant, ParticipantStatus
from .models import Interview, InterviewStatus, InterviewStatusHistory

logger = logging.getLogger(__name__)


def _complete_assignment(assignment):
    """Mark an assignment as completed, handling the case where a completed
    assignment already exists for this participant+enumerator combination
    (e.g. after a re-assignment following a previous completion)."""
    try:
        with transaction.atomic():
            assignment.status = AssignmentStatus.COMPLETED
            assignment.completed_at = timezone.now()
            assignment.save(update_fields=['status', 'completed_at'])
    except IntegrityError:
        Assignment.objects.filter(pk=assignment.pk).update(
            status=AssignmentStatus.COMPLETED,
            completed_at=timezone.now(),
        )


class InterviewListView(LoginRequiredMixin, ListView):
    template_name = 'interviews/interview_list.html'
    context_object_name = 'interviews'
    paginate_by = 25

    # Badge colours reused in both code paths
    _BADGE = {
        InterviewStatus.PENDING: 'secondary',
        InterviewStatus.ASSIGNED: 'primary',
        InterviewStatus.IN_PROGRESS: 'warning',
        InterviewStatus.COMPLETED: 'success',
        InterviewStatus.REFUSED: 'danger',
        InterviewStatus.UNREACHABLE: 'dark',
        InterviewStatus.CALLBACK_REQUIRED: 'info',
    }

    def get_queryset(self):
        from apps.assignments.models import Assignment
        user = self.request.user

        if user.is_supervisor():
            # Base from Assignment so ALL assigned participants appear,
            # even those with no interview record yet.
            qs = Assignment.objects.select_related(
                'participant', 'participant__partner', 'enumerator'
            ).prefetch_related('interview').filter(enumerator__supervisor=user)
            enumerator_id = self.request.GET.get('enumerator')
            if enumerator_id:
                qs = qs.filter(enumerator_id=enumerator_id)
            status = self.request.GET.get('status')
            if status:
                # Filter on related interview status; exclude rows with no
                # interview when filtering for a specific status
                qs = qs.filter(interview__status=status)
            return qs

        # Admin and enumerator: Interview-based queryset (original behaviour)
        qs = Interview.objects.select_related('participant', 'enumerator', 'participant__partner')
        if user.is_enumerator():
            qs = qs.filter(enumerator=user)
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        enumerator_id = self.request.GET.get('enumerator')
        if enumerator_id:
            qs = qs.filter(enumerator_id=enumerator_id)
        return qs

    def get_context_data(self, **kwargs):
        from apps.accounts.models import CustomUser
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = InterviewStatus.choices
        user = self.request.user
        ctx['is_supervisor_view'] = user.is_supervisor()

        if user.is_supervisor():
            label_map = dict(InterviewStatus.choices)
            for a in ctx['interviews']:
                try:
                    iv = a.interview
                    a.iv_status = iv.status
                    a.iv_badge = self._BADGE.get(iv.status, 'secondary')
                    a.iv_display = label_map.get(iv.status, iv.status)
                    a.iv_pk = iv.pk
                    a.iv_remarks = iv.remarks
                    a.iv_callback = iv.callback_date
                    a.iv_scheduled = iv.scheduled_date
                    a.iv_updated = iv.updated_at
                except Exception:
                    a.iv_status = None
                    a.iv_badge = 'secondary'
                    a.iv_display = 'Not Started'
                    a.iv_pk = None
                    a.iv_remarks = ''
                    a.iv_callback = None
                    a.iv_scheduled = None
                    a.iv_updated = a.assigned_at
            ctx['enumerators'] = CustomUser.objects.filter(
                supervisor=user, is_active=True
            ).order_by('first_name', 'last_name')
        elif user.is_admin():
            ctx['enumerators'] = CustomUser.objects.filter(
                role='enumerator', is_active=True
            ).order_by('first_name', 'last_name')
        else:
            ctx['enumerators'] = []
        return ctx


class InterviewDetailView(LoginRequiredMixin, DetailView):
    model = Interview
    template_name = 'interviews/interview_detail.html'
    context_object_name = 'interview'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_history'] = self.object.status_history.order_by('-changed_at')
        ctx['statuses'] = InterviewStatus.choices
        return ctx


class InterviewUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        interview = get_object_or_404(Interview, pk=pk)
        allowed = [interview.enumerator]
        if request.user not in allowed and not (request.user.is_admin() or request.user.is_supervisor()):
            messages.error(request, 'Permission denied.')
            return redirect('interviews:list')
        new_status = request.POST.get('status')
        remarks = request.POST.get('remarks', '')
        callback_date = request.POST.get('callback_date') or None
        old_status = interview.status
        InterviewStatusHistory.objects.create(
            interview=interview,
            changed_by=request.user,
            previous_status=old_status,
            new_status=new_status,
            notes=remarks,
        )
        interview.status = new_status
        interview.remarks = remarks
        if callback_date:
            interview.callback_date = callback_date
        if new_status == InterviewStatus.COMPLETED:
            from django.utils import timezone
            interview.completed_at = timezone.now()
            interview.participant.status = ParticipantStatus.INTERVIEWED
            interview.participant.save(update_fields=['status'])
        elif new_status == InterviewStatus.IN_PROGRESS and not interview.started_at:
            from django.utils import timezone
            interview.started_at = timezone.now()
        interview.save()
        log_action(request, 'INTERVIEW_UPDATE', 'interviews', pk,
                   old_values={'status': old_status},
                   new_values={'status': new_status},
                   description=f'Interview {pk} updated to {new_status}')
        messages.success(request, 'Interview status updated.')
        return redirect('interviews:detail', pk=pk)


class InterviewCreateView(LoginRequiredMixin, View):
    """Create interview for an assigned participant."""
    def post(self, request, participant_pk):
        participant = get_object_or_404(Participant, pk=participant_pk)
        if Interview.objects.filter(participant=participant, status__in=[
            InterviewStatus.PENDING, InterviewStatus.ASSIGNED, InterviewStatus.IN_PROGRESS
        ]).exists():
            messages.warning(request, 'An active interview already exists for this participant.')
            return redirect('participants:detail', pk=participant_pk)
        from apps.assignments.models import Assignment
        assignment = Assignment.objects.filter(participant=participant, status='active').first()
        interview = Interview.objects.create(
            participant=participant,
            assignment=assignment,
            enumerator=assignment.enumerator if assignment else request.user,
            status=InterviewStatus.ASSIGNED,
        )
        log_action(request, 'CREATE_INTERVIEW', 'interviews', interview.pk,
                   description=f'Interview created for {participant.pseudo_code}')
        messages.success(request, f'Interview created for {participant.pseudo_code}.')
        return redirect('interviews:detail', pk=interview.pk)


class QuickInterviewUpdateView(LoginRequiredMixin, View):
    """
    One-step view for enumerators to record an interview outcome directly
    from the My Assignments page.  Creates the Interview record if it does
    not exist yet, then applies the chosen status.
    """
    def post(self, request, assignment_pk):
        from apps.assignments.models import Assignment, AssignmentStatus
        assignment = get_object_or_404(Assignment, pk=assignment_pk)

        # Only the assigned enumerator (or admin/supervisor) may update
        if not (
            request.user == assignment.enumerator
            or request.user.is_admin()
            or request.user.is_supervisor()
        ):
            messages.error(request, 'Permission denied.')
            return redirect('assignments:mine')

        new_status = request.POST.get('status')
        remarks = request.POST.get('remarks', '').strip()
        callback_date = request.POST.get('callback_date') or None

        if new_status not in dict(InterviewStatus.choices):
            messages.error(request, 'Invalid status selected.')
            return redirect('assignments:mine')

        # Find existing interview for this participant (however it was created),
        # fall back to creating a fresh one linked to the assignment.
        interview = (
            Interview.objects.filter(assignment=assignment).first()
            or Interview.objects.filter(participant=assignment.participant).first()
        )
        if interview is None:
            interview = Interview.objects.create(
                participant=assignment.participant,
                assignment=assignment,
                enumerator=assignment.enumerator,
                status=InterviewStatus.ASSIGNED,
            )
        else:
            # Make sure the interview is linked to this assignment
            if not interview.assignment_id:
                interview.assignment = assignment
            if not interview.enumerator_id:
                interview.enumerator = assignment.enumerator

        old_status = interview.status

        InterviewStatusHistory.objects.create(
            interview=interview,
            changed_by=request.user,
            previous_status=old_status,
            new_status=new_status,
            notes=remarks,
        )

        interview.status = new_status
        interview.remarks = remarks
        if callback_date:
            interview.callback_date = callback_date
        if new_status == InterviewStatus.COMPLETED:
            interview.completed_at = timezone.now()
            interview.participant.status = ParticipantStatus.INTERVIEWED
            interview.participant.save(update_fields=['status'])
            _complete_assignment(assignment)
        elif new_status in (InterviewStatus.REFUSED, InterviewStatus.UNREACHABLE):
            _complete_assignment(assignment)

        interview.save()

        log_action(request, 'INTERVIEW_UPDATE', 'interviews', interview.pk,
                   old_values={'status': old_status},
                   new_values={'status': new_status},
                   description=f'Quick update: {interview.participant.pseudo_code} → {new_status}')

        status_labels = {
            InterviewStatus.COMPLETED: 'Marked as interviewed',
            InterviewStatus.REFUSED: 'Marked as refused',
            InterviewStatus.UNREACHABLE: 'Marked as unreachable',
            InterviewStatus.CALLBACK_REQUIRED: 'Callback scheduled',
            InterviewStatus.IN_PROGRESS: 'Marked as in progress',
        }
        messages.success(request, f'{status_labels.get(new_status, "Status updated")} — {interview.participant.pseudo_code}.')
        next_url = request.POST.get('next') or 'assignments:mine'
        return redirect(next_url)
