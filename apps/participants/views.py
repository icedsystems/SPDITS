import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView
from django.utils import timezone

from apps.audit.utils import log_action
from .models import Participant, IdentityMap, ReIdentificationLog, ParticipantStatus

logger = logging.getLogger(__name__)

DIRECT_IDENTIFIER_FIELDS = ['name', 'full_name', 'national_id', 'id_number', 'passport', 'phone', 'phone_number', 'email', 'address', 'exact_address']


class ParticipantListView(LoginRequiredMixin, ListView):
    model = Participant
    template_name = 'participants/participant_list.html'
    context_object_name = 'participants'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('partner', 'upload_batch')
        user = self.request.user
        if user.is_partner() and user.partner:
            qs = qs.filter(partner=user.partner)
        q = self.request.GET.get('q')
        status = self.request.GET.get('status')
        partner = self.request.GET.get('partner')
        if q:
            qs = qs.filter(pseudo_code__icontains=q)
        if status:
            qs = qs.filter(status=status)
        if partner and user.is_admin():
            qs = qs.filter(partner_id=partner)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = ParticipantStatus.choices
        from apps.accounts.models import Partner
        ctx['partners'] = Partner.objects.filter(is_active=True)
        return ctx


class ParticipantDetailView(LoginRequiredMixin, DetailView):
    model = Participant
    template_name = 'participants/participant_detail.html'
    context_object_name = 'participant'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        p = self.object
        ctx['tracing_logs'] = p.tracing_logs.order_by('-created_at')[:10]
        ctx['can_reidentify'] = self.request.user.can_reidentify()
        ctx['reidentification_logs'] = p.reidentification_logs.order_by('-viewed_at')[:5]
        return ctx


class ReIdentifyView(LoginRequiredMixin, View):
    """Securely reveal direct identifiers for an authorized user."""
    template_name = 'participants/reidentify.html'

    def post(self, request, pk):
        if not request.user.can_reidentify():
            messages.error(request, 'You are not authorized to re-identify participants.')
            return redirect('participants:detail', pk=pk)
        participant = get_object_or_404(Participant, pk=pk)
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, 'A reason must be provided for re-identification.')
            return redirect('participants:detail', pk=pk)
        try:
            identity = participant.identity_map
            identifiers = identity.get_identifiers()
        except IdentityMap.DoesNotExist:
            messages.error(request, 'No identity mapping found for this participant.')
            return redirect('participants:detail', pk=pk)

        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
        ReIdentificationLog.objects.create(
            participant=participant,
            requested_by=request.user,
            reason=reason,
            ip_address=ip.split(',')[0].strip() or None,
            session_id=request.session.session_key or '',
            fields_accessed=list(identifiers.keys()),
        )
        log_action(request, 'REIDENTIFY', 'participants', pk,
                   description=f'{request.user.email} re-identified {participant.pseudo_code}. Reason: {reason}')
        return render(request, self.template_name, {
            'participant': participant,
            'identifiers': identifiers,
            'reason': reason,
            'revealed_at': timezone.now(),
        })


class ParticipantExportView(LoginRequiredMixin, View):
    def get(self, request):
        import csv
        from io import StringIO
        if not (request.user.is_admin() or request.user.is_supervisor()):
            messages.error(request, 'Permission denied.')
            return redirect('participants:list')
        qs = Participant.objects.select_related('partner').filter(status=ParticipantStatus.TRACED)
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Pseudocode', 'Partner', 'Status', 'County', 'Gender', 'Age'])
        for p in qs:
            d = p.data
            writer.writerow([
                p.pseudo_code, p.partner.name, p.status,
                d.get('county', ''), d.get('gender', ''), d.get('age', ''),
            ])
        log_action(request, 'EXPORT_PARTICIPANTS', 'participants', description='Exported participant list')
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="participants_traced.csv"'
        return response
