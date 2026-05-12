import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView

from apps.audit.utils import log_action
from apps.participants.models import Participant, ParticipantStatus
from .models import Interview, InterviewStatus, InterviewStatusHistory

logger = logging.getLogger(__name__)


class InterviewListView(LoginRequiredMixin, ListView):
    model = Interview
    template_name = 'interviews/interview_list.html'
    context_object_name = 'interviews'
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user
        qs = Interview.objects.select_related('participant', 'enumerator', 'participant__partner')
        if user.is_enumerator():
            qs = qs.filter(enumerator=user)
        elif user.is_supervisor():
            qs = qs.filter(enumerator__supervisor=user)
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = InterviewStatus.choices
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

        # Get or create the interview for this assignment
        interview, created = Interview.objects.get_or_create(
            assignment=assignment,
            defaults={
                'participant': assignment.participant,
                'enumerator': assignment.enumerator,
                'status': InterviewStatus.ASSIGNED,
            }
        )

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
            assignment.status = AssignmentStatus.COMPLETED
            assignment.completed_at = timezone.now()
            assignment.save(update_fields=['status', 'completed_at'])
        elif new_status in (InterviewStatus.REFUSED, InterviewStatus.UNREACHABLE):
            assignment.status = AssignmentStatus.COMPLETED
            assignment.completed_at = timezone.now()
            assignment.save(update_fields=['status', 'completed_at'])

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
        return redirect('assignments:mine')
