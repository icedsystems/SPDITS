import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, CreateView

from apps.audit.utils import log_action
from apps.accounts.models import CustomUser
from apps.notifications.tasks import send_invitation_email
from .forms import InvitationCreateForm, InvitationAcceptForm
from .models import Invitation, InvitationStatus

logger = logging.getLogger(__name__)


class InvitationListView(LoginRequiredMixin, ListView):
    model = Invitation
    template_name = 'invitations/invitation_list.html'
    context_object_name = 'invitations'
    paginate_by = 25

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
            send_invitation_email.delay(invitation.pk)
            log_action(request, 'SEND_INVITATION', 'invitations', invitation.pk,
                       description=f'Invitation sent to {invitation.email}')
            messages.success(request, f'Invitation sent to {invitation.email}.')
            return redirect('invitations:list')
        return render(request, self.template_name, {'form': form})


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
