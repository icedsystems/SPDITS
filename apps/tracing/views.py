import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView

from apps.accounts.models import Partner
from apps.audit.utils import log_action
from apps.participants.models import Participant, ParticipantStatus
from .forms import TracingUpdateForm
from .models import TracingLog

logger = logging.getLogger(__name__)


class TracingQueueView(LoginRequiredMixin, ListView):
    model = Participant
    template_name = 'tracing/tracing_queue.html'
    context_object_name = 'participants'
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user
        qs = Participant.objects.filter(
            status__in=[ParticipantStatus.UPLOADED, ParticipantStatus.TRACING]
        ).select_related('partner')
        if user.is_partner() and user.partner:
            qs = qs.filter(partner=user.partner)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(pseudo_code__icontains=q)
        partner_id = self.request.GET.get('partner')
        if partner_id and not (user.is_partner() and user.partner):
            qs = qs.filter(partner_id=partner_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = TracingUpdateForm()
        ctx['update_url'] = 'tracing:update'
        user = self.request.user
        if not (user.is_partner() and user.partner):
            ctx['partners'] = Partner.objects.filter(is_active=True).order_by('name')
        ctx['selected_partner'] = self.request.GET.get('partner', '')
        return ctx


class TracingUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        allowed_roles = ['system_admin', 'tracer', 'supervisor']
        if request.user.role not in allowed_roles:
            messages.error(request, 'Permission denied.')
            return redirect('tracing:queue')
        participant = get_object_or_404(Participant, pk=pk)
        form = TracingUpdateForm(request.POST)
        if form.is_valid():
            new_status = form.cleaned_data['new_status']
            old_status = participant.status
            TracingLog.objects.create(
                participant=participant,
                updated_by=request.user,
                previous_status=old_status,
                new_status=new_status,
                notes=form.cleaned_data['notes'],
                contact_attempted=form.cleaned_data['contact_attempted'],
                contact_method=form.cleaned_data['contact_method'],
                location_found=form.cleaned_data['location_found'],
            )
            participant.status = new_status
            participant.save(update_fields=['status'])
            log_action(request, 'TRACING_UPDATE', 'tracing', pk,
                       old_values={'status': old_status},
                       new_values={'status': new_status},
                       description=f'Tracing updated for {participant.pseudo_code}')
            messages.success(request, f'{participant.pseudo_code} status updated to {new_status}.')
        else:
            messages.error(request, 'Invalid form data.')
        if request.htmx:
            from django.http import HttpResponse
            return HttpResponse(f'<span class="badge bg-info">{new_status}</span>')
        return redirect('tracing:queue')


class TracedQueueView(LoginRequiredMixin, ListView):
    model = Participant
    template_name = 'tracing/traced_queue.html'
    context_object_name = 'participants'
    paginate_by = 25

    def get_queryset(self):
        return Participant.objects.filter(
            status=ParticipantStatus.TRACED
        ).select_related('partner')


class TracerContactView(LoginRequiredMixin, View):
    """Show decrypted contact details to tracers/supervisors/admins. Fully audited."""

    def post(self, request, pk):
        if not request.user.can_view_contacts():
            messages.error(request, 'You do not have permission to view contact details.')
            return redirect('tracing:queue')

        participant = get_object_or_404(
            Participant,
            pk=pk,
            status__in=[ParticipantStatus.UPLOADED, ParticipantStatus.TRACING]
        )

        try:
            from apps.participants.models import IdentityMap
            identity = participant.identity_map
            contacts = identity.get_identifiers()
        except Exception:
            messages.error(request, 'No contact information found for this participant.')
            return redirect('tracing:queue')

        log_action(
            request,
            'TRACER_CONTACT_VIEW',
            'tracing',
            pk,
            description=f'{request.user.email} viewed contacts for {participant.pseudo_code}',
        )

        return render(request, 'tracing/tracer_contact.html', {
            'participant': participant,
            'contacts': contacts,
        })


class TracingHistoryView(LoginRequiredMixin, ListView):
    model = TracingLog
    template_name = 'tracing/tracing_history.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        pk = self.kwargs.get('participant_pk')
        return TracingLog.objects.filter(participant_id=pk).select_related('updated_by')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['participant'] = get_object_or_404(Participant, pk=self.kwargs['participant_pk'])
        return ctx
