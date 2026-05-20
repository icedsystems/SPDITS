import hashlib
import logging
import secrets
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from apps.audit.utils import log_action
from apps.accounts.models import CustomUser
from .forms import InvitationCreateForm, InvitationAcceptForm
from .models import Invitation, InvitationStatus

logger = logging.getLogger(__name__)


def _send_invitation_now(invitation):
    """Send invitation email synchronously via the configured email backend."""
    from django.conf import settings
    from django.core.mail import send_mail
    from django.template.loader import render_to_string

    context = {
        'invitation': invitation,
        'accept_url': invitation.get_accept_url,
        'expiry_minutes': settings.INVITATION_EXPIRY_MINUTES,
    }
    body = render_to_string('emails/invitation.txt', context)
    html = render_to_string('emails/invitation.html', context)
    send_mail(
        subject='[ICED SPDITS] You have been invited',
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invitation.email],
        html_message=html,
        fail_silently=False,
    )


class InvitationListView(LoginRequiredMixin, ListView):
    model = Invitation
    template_name = 'invitations/invitation_list.html'
    context_object_name = 'invitations'

    def get_queryset(self):
        return super().get_queryset().select_related('invited_by', 'partner')


class InvitationCreateView(LoginRequiredMixin, View):
    template_name = 'invitations/invitation_form.html'

    def get(self, request):
        if not request.user.is_admin():
            messages.error(request, 'Only administrators can send invitations.')
            return redirect('dashboards:home')
        form = InvitationCreateForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        if not request.user.is_admin():
            messages.error(request, 'Permission denied.')
            return redirect('dashboards:home')
        form = InvitationCreateForm(request.POST)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.invited_by = request.user
            invitation.save()
            try:
                _send_invitation_now(invitation)
                messages.success(request, f'Invitation sent to {invitation.email}.')
            except Exception as e:
                logger.exception(f'Failed to send invitation email to {invitation.email}: {e}')
                messages.warning(
                    request,
                    f'Invitation created but email delivery failed: {e}. '
                    f'Use the Resend button to try again.'
                )
            log_action(request, 'SEND_INVITATION', 'invitations', invitation.pk,
                       description=f'Invitation sent to {invitation.email}')
            return redirect('invitations:list')
        return render(request, self.template_name, {'form': form})


class InvitationResendView(LoginRequiredMixin, View):
    """Regenerate token + expiry and resend the invitation email immediately."""

    def post(self, request, pk):
        invitation = get_object_or_404(Invitation, pk=pk)
        if not request.user.is_admin():
            messages.error(request, 'Permission denied.')
            return redirect('invitations:list')

        if invitation.status == InvitationStatus.ACCEPTED:
            messages.error(request, 'This invitation has already been accepted.')
            return redirect('invitations:list')

        from django.conf import settings
        new_token = secrets.token_urlsafe(64)
        invitation.token = new_token
        invitation.token_hash = hashlib.sha256(new_token.encode()).hexdigest()
        invitation.status = InvitationStatus.PENDING
        invitation.expiry_time = timezone.now() + timedelta(minutes=settings.INVITATION_EXPIRY_MINUTES)
        invitation.save()

        try:
            _send_invitation_now(invitation)
            messages.success(
                request,
                f'Invitation resent to {invitation.email}. New link expires in '
                f'{settings.INVITATION_EXPIRY_MINUTES} minutes.'
            )
        except Exception as e:
            logger.exception(f'Resend failed for {invitation.email}: {e}')
            messages.error(request, f'Failed to resend invitation: {e}')

        log_action(request, 'RESEND_INVITATION', 'invitations', pk,
                   description=f'Invitation resent to {invitation.email}')
        return redirect('invitations:list')


class InvitationRevokeView(LoginRequiredMixin, View):
    def post(self, request, pk):
        invitation = get_object_or_404(Invitation, pk=pk)
        if not request.user.is_admin():
            messages.error(request, 'Permission denied.')
            return redirect('invitations:list')
        invitation.status = InvitationStatus.REVOKED
        invitation.save(update_fields=['status'])
        log_action(request, 'REVOKE_INVITATION', 'invitations', pk,
                   description=f'Revoked invitation for {invitation.email}')
        messages.success(request, 'Invitation revoked.')
        return redirect('invitations:list')


class InvitationAcceptView(View):
    template_name = 'invitations/accept.html'

    def get(self, request, token):
        invitation = get_object_or_404(Invitation, token=token)
        if not invitation.is_valid():
            return render(request, 'invitations/invalid.html', {'invitation': invitation})
        form = InvitationAcceptForm(initial={'username': invitation.email.split('@')[0]})
        return render(request, self.template_name, {'invitation': invitation, 'form': form})

    def post(self, request, token):
        invitation = get_object_or_404(Invitation, token=token)
        if not invitation.is_valid():
            return render(request, 'invitations/invalid.html', {'invitation': invitation})
        form = InvitationAcceptForm(request.POST)
        if form.is_valid():
            user = CustomUser.objects.create_user(
                username=form.cleaned_data['username'],
                email=invitation.email,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                password=form.cleaned_data['password'],
                role=invitation.role,
                partner=invitation.partner,
                is_invitation_accepted=True,
            )
            invitation.mark_accepted(user)
            log_action(request, 'ACCEPT_INVITATION', 'invitations', invitation.pk,
                       description=f'{user.email} accepted invitation')
            messages.success(request, 'Account created! Please log in.')
            return redirect('accounts:login')
        return render(request, self.template_name, {'invitation': invitation, 'form': form})
