import logging
import csv
from io import StringIO
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from apps.accounts.models import CustomUser, Role
from apps.audit.utils import log_action
from apps.participants.models import Participant, ParticipantStatus, IdentityMap
from .models import Assignment, AssignmentStatus, AssignmentExportToken

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


def _build_assignment_csv(assignments):
    """Build a CSV string with full identity data for the given assignments."""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Pseudocode', 'Full Name', 'National ID', 'Passport', 'Phone',
        'Alt Phone', 'Email', 'Address',
        'Partner', 'County', 'Sub-County', 'Ward', 'Gender', 'Age',
        'Assignment Date', 'Notes',
    ])
    for a in assignments:
        p = a.participant
        d = p.data
        identity = {}
        try:
            identity = p.identity_map.get_identifiers()
        except IdentityMap.DoesNotExist:
            pass
        writer.writerow([
            p.pseudo_code,
            identity.get('name') or '',
            identity.get('national_id') or '',
            identity.get('passport') or '',
            identity.get('phone') or '',
            identity.get('alt_phone') or '',
            identity.get('email') or '',
            identity.get('address') or '',
            p.partner.name,
            d.get('county', ''),
            d.get('sub_county', ''),
            d.get('ward', ''),
            d.get('gender', ''),
            d.get('age', ''),
            a.assigned_at.strftime('%Y-%m-%d %H:%M'),
            a.notes,
        ])
    return output.getvalue()


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

        created_assignments = []
        assigned_count = 0
        for pid in participant_ids:
            try:
                p = Participant.objects.get(pk=pid, status=ParticipantStatus.TRACED)
                a = Assignment.objects.create(
                    participant=p, enumerator=enumerator,
                    supervisor=request.user if request.user.is_supervisor() else enumerator.supervisor,
                    notes=notes
                )
                p.status = ParticipantStatus.ASSIGNED
                p.save(update_fields=['status'])
                created_assignments.append(a)
                assigned_count += 1
            except (Participant.DoesNotExist, Exception) as e:
                logger.warning(f'Assignment error for participant {pid}: {e}')

        log_action(request, 'BULK_ASSIGN', 'assignments',
                   description=f'Assigned {assigned_count} participants to {enumerator.get_full_name()}')

        if created_assignments:
            try:
                _generate_and_notify(request, enumerator, created_assignments)
            except Exception as e:
                logger.exception(f'Failed to generate assignment export for enumerator {enumerator.pk}: {e}')

        messages.success(
            request,
            f'{assigned_count} participants assigned to {enumerator.get_full_name()}. '
            f'A secure download link has been sent to their email.'
        )
        return redirect('assignments:queue')


def _generate_and_notify(request, enumerator, assignments):
    """Generate a timed CSV token and notify the enumerator."""
    from django.conf import settings
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from apps.notifications.models import Notification, NotificationType

    assignments_qs = Assignment.objects.filter(
        pk__in=[a.pk for a in assignments]
    ).select_related('participant', 'participant__partner', 'participant__identity_map')

    csv_data = _build_assignment_csv(assignments_qs)

    export_token = AssignmentExportToken.objects.create(
        enumerator=enumerator,
        assigned_by=request.user,
        participant_count=len(assignments),
        csv_data=csv_data,
    )

    app_url = getattr(settings, 'APP_URL', 'https://ea.data.iced-eval.org')
    download_url = f"{app_url}/assignments/download/{export_token.token}/"

    Notification.objects.create(
        recipient=enumerator,
        notification_type=NotificationType.ASSIGNMENT,
        title=f'{len(assignments)} new participant(s) assigned to you',
        message=(
            f'{request.user.get_full_name()} has assigned {len(assignments)} participant(s) to you. '
            f'Download the secure CSV (expires in 30 minutes).'
        ),
        link=f'/assignments/download/{export_token.token}/',
    )

    if enumerator.email:
        context = {
            'enumerator': enumerator,
            'assigned_by': request.user.get_full_name(),
            'participant_count': len(assignments),
            'download_url': download_url,
            'expires_at': export_token.expires_at,
        }
        try:
            html = render_to_string('emails/assignment_csv.html', context)
            body = render_to_string('emails/assignment_csv.txt', context)
            send_mail(
                subject=f'[ICED SPDITS] {len(assignments)} participant(s) assigned — download CSV',
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[enumerator.email],
                html_message=html,
                fail_silently=True,
            )
        except Exception as e:
            logger.warning(f'Assignment email to {enumerator.email} failed: {e}')


class SecureCSVDownloadView(View):
    """Public (token-authenticated) view to download the assignment CSV."""

    def get(self, request, token):
        try:
            export = AssignmentExportToken.objects.select_related('enumerator').get(token=token)
        except AssignmentExportToken.DoesNotExist:
            raise Http404('Download link not found.')

        if not export.is_valid():
            return HttpResponse(
                '<h2>This download link has expired.</h2>'
                '<p>Download links are valid for 30 minutes only. '
                'Ask your supervisor to re-assign to generate a new link.</p>',
                status=410,
            )

        if not export.downloaded_at:
            export.downloaded_at = timezone.now()
            export.save(update_fields=['downloaded_at'])

        log_action(
            request, 'DOWNLOAD_ASSIGNMENT_CSV', 'assignments',
            description=(
                f'Assignment CSV downloaded for {export.enumerator.get_full_name()} '
                f'({export.participant_count} participants)'
            )
        )

        filename = f'assignments_{export.enumerator.username}_{export.created_at.strftime("%Y%m%d_%H%M")}.csv'
        response = HttpResponse(export.csv_data, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class MyAssignmentsView(LoginRequiredMixin, ListView):
    """Enumerator's personal assignment list."""
    model = Assignment
    template_name = 'assignments/my_assignments.html'
    context_object_name = 'assignments'
    paginate_by = 25

    def get_queryset(self):
        return Assignment.objects.filter(
            enumerator=self.request.user,
        ).select_related('participant', 'participant__partner').prefetch_related('interview')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.interviews.models import InterviewStatus
        badge_map = {
            InterviewStatus.PENDING: 'secondary',
            InterviewStatus.ASSIGNED: 'primary',
            InterviewStatus.IN_PROGRESS: 'warning',
            InterviewStatus.COMPLETED: 'success',
            InterviewStatus.REFUSED: 'danger',
            InterviewStatus.UNREACHABLE: 'dark',
            InterviewStatus.CALLBACK_REQUIRED: 'info',
        }
        label_map = dict(InterviewStatus.choices)
        for a in ctx['assignments']:
            try:
                iv = a.interview
                a.interview_status = iv.status
                a.interview_badge = badge_map.get(iv.status, 'secondary')
                a.interview_status_display = label_map.get(iv.status, iv.status)
            except Exception:
                a.interview_status = None
                a.interview_badge = 'secondary'
                a.interview_status_display = 'Not Started'
        return ctx


class AssignmentListView(LoginRequiredMixin, ListView):
    model = Assignment
    template_name = 'assignments/assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 25

    def get_queryset(self):
        from apps.interviews.models import InterviewStatus
        user = self.request.user
        qs = Assignment.objects.select_related(
            'participant', 'participant__partner', 'enumerator', 'supervisor'
        ).prefetch_related('interview')
        if user.is_enumerator():
            qs = qs.filter(enumerator=user)
        elif user.is_supervisor():
            qs = qs.filter(enumerator__supervisor=user)
        enumerator_id = self.request.GET.get('enumerator')
        if enumerator_id:
            qs = qs.filter(enumerator_id=enumerator_id)
        interview_status = self.request.GET.get('interview_status')
        if interview_status:
            qs = qs.filter(interview__status=interview_status)
        return qs

    def get_context_data(self, **kwargs):
        from apps.accounts.models import CustomUser
        from apps.interviews.models import InterviewStatus
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        badge_map = {
            InterviewStatus.PENDING: 'secondary',
            InterviewStatus.ASSIGNED: 'primary',
            InterviewStatus.IN_PROGRESS: 'warning',
            InterviewStatus.COMPLETED: 'success',
            InterviewStatus.REFUSED: 'danger',
            InterviewStatus.UNREACHABLE: 'dark',
            InterviewStatus.CALLBACK_REQUIRED: 'info',
        }
        label_map = dict(InterviewStatus.choices)
        for a in ctx['assignments']:
            try:
                iv = a.interview
                a.interview_status = iv.status
                a.interview_badge = badge_map.get(iv.status, 'secondary')
                a.interview_status_display = label_map.get(iv.status, iv.status)
                a.interview_pk = iv.pk
            except Exception:
                a.interview_status = None
                a.interview_badge = 'secondary'
                a.interview_status_display = 'Not Started'
                a.interview_pk = None

        ctx['interview_statuses'] = InterviewStatus.choices
        if user.is_supervisor():
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
