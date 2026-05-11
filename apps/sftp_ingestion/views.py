from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from .models import SFTPIngestionLog, SFTPConfig
from apps.audit.utils import log_action


class SFTPLogListView(LoginRequiredMixin, ListView):
    model = SFTPIngestionLog
    template_name = 'sftp_ingestion/sftp_log_list.html'
    context_object_name = 'logs'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('partner', 'upload_batch')
        if not self.request.user.is_admin():
            if self.request.user.partner:
                qs = qs.filter(partner=self.request.user.partner)
        return qs


class SFTPConfigListView(LoginRequiredMixin, ListView):
    model = SFTPConfig
    template_name = 'sftp_ingestion/sftp_config_list.html'
    context_object_name = 'configs'

    def get_queryset(self):
        if not self.request.user.is_admin():
            messages.error(self.request, 'Permission denied.')
            return SFTPConfig.objects.none()
        return super().get_queryset().select_related('partner')


class SFTPConfigCreateView(LoginRequiredMixin, CreateView):
    model = SFTPConfig
    fields = ['partner', 'username', 'inbound_directory', 'processing_directory',
              'archive_directory', 'failed_directory', 'is_active']
    template_name = 'sftp_ingestion/sftp_config_form.html'
    success_url = reverse_lazy('sftp:config_list')

    def form_valid(self, form):
        if not self.request.user.is_admin():
            messages.error(self.request, 'Permission denied.')
            return redirect('dashboards:home')
        response = super().form_valid(form)
        log_action(self.request, 'CREATE_SFTP_CONFIG', 'sftp_ingestion', self.object.pk,
                   description=f'Created SFTP config for {self.object.partner.name}')
        messages.success(self.request, 'SFTP configuration saved.')
        return response


class SFTPConfigEditView(LoginRequiredMixin, UpdateView):
    model = SFTPConfig
    fields = ['username', 'inbound_directory', 'processing_directory',
              'archive_directory', 'failed_directory', 'is_active']
    template_name = 'sftp_ingestion/sftp_config_form.html'
    success_url = reverse_lazy('sftp:config_list')
