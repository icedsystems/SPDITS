import hashlib
import logging
import os
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView

from apps.audit.utils import log_action
from apps.notifications.tasks import notify_admin_new_upload
from apps.processing.tasks import process_upload_batch
from .forms import FileUploadForm, UploadApprovalForm
from .models import UploadBatch, BatchStatus

logger = logging.getLogger(__name__)


class UploadListView(LoginRequiredMixin, ListView):
    model = UploadBatch
    template_name = 'uploads/upload_list.html'
    context_object_name = 'batches'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('partner', 'uploaded_by')
        user = self.request.user
        if user.is_partner() and user.partner:
            qs = qs.filter(partner=user.partner)
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['batch_statuses'] = BatchStatus.choices
        ctx['pending_count'] = UploadBatch.objects.filter(status=BatchStatus.PENDING_APPROVAL).count()
        return ctx


class UploadCreateView(LoginRequiredMixin, View):
    template_name = 'uploads/upload_form.html'

    def get(self, request):
        form = FileUploadForm(user=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = FileUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            f = request.FILES['file']
            md5 = hashlib.md5(f.read()).hexdigest()
            f.seek(0)
            ext = '.' + f.name.rsplit('.', 1)[-1].lower()
            batch = UploadBatch(
                partner=form.cleaned_data['partner'],
                uploaded_by=request.user,
                file=f,
                original_filename=f.name,
                file_size=f.size,
                file_type=ext.lstrip('.').upper(),
                checksum_md5=md5,
                source='web',
            )
            batch.save()
            task = process_upload_batch.delay(batch.pk)
            batch.celery_task_id = task.id
            batch.status = BatchStatus.PROCESSING
            batch.save(update_fields=['celery_task_id', 'status'])
            log_action(request, 'FILE_UPLOAD', 'uploads', batch.pk,
                       description=f'Uploaded {f.name} for {batch.partner.name}')
            messages.success(request, f'File "{f.name}" uploaded and queued for processing.')
            return redirect('uploads:detail', pk=batch.pk)
        return render(request, self.template_name, {'form': form})


class UploadDetailView(LoginRequiredMixin, DetailView):
    model = UploadBatch
    template_name = 'uploads/upload_detail.html'
    context_object_name = 'batch'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['approval_form'] = UploadApprovalForm()
        ctx['can_approve_uploads'] = self.request.user.can_approve_uploads()
        return ctx


class UploadApprovalView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if not request.user.can_approve_uploads():
            messages.error(request, 'Permission denied.')
            return redirect('uploads:detail', pk=pk)
        batch = get_object_or_404(UploadBatch, pk=pk)
        form = UploadApprovalForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            notes = form.cleaned_data['notes']
            if action == 'approve':
                batch.approve(request.user, notes)
                from apps.processing.tasks import pseudocode_batch_participants
                pseudocode_batch_participants.delay(batch.pk)
                log_action(request, 'APPROVE_UPLOAD', 'uploads', batch.pk,
                           description=f'Approved batch {batch.batch_id}')
                messages.success(request, f'Batch {batch.batch_id} approved. Pseudocoding started.')
            else:
                batch.reject(request.user, notes)
                log_action(request, 'REJECT_UPLOAD', 'uploads', batch.pk,
                           description=f'Rejected batch {batch.batch_id}: {notes}')
                messages.warning(request, f'Batch {batch.batch_id} rejected.')
        return redirect('uploads:detail', pk=pk)


class UploadPendingView(LoginRequiredMixin, ListView):
    model = UploadBatch
    template_name = 'uploads/upload_pending.html'
    context_object_name = 'batches'

    def get_queryset(self):
        return UploadBatch.objects.filter(status=BatchStatus.PENDING_APPROVAL).select_related('partner', 'uploaded_by')


class UploadDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        batch = get_object_or_404(UploadBatch, pk=pk)
        user = request.user

        # Permission: admin, supervisor, or the partner who owns the batch
        if user.is_partner():
            if not user.partner or user.partner != batch.partner:
                messages.error(request, 'You do not have permission to download this file.')
                return redirect('uploads:detail', pk=pk)
        elif not (user.is_admin() or user.is_supervisor()):
            messages.error(request, 'You do not have permission to download this file.')
            return redirect('uploads:detail', pk=pk)

        if not batch.file:
            raise Http404('No file attached to this batch.')

        file_path = batch.file.path
        if not os.path.exists(file_path):
            raise Http404('File not found on disk.')

        log_action(request, 'DOWNLOAD_UPLOAD', 'uploads', batch.pk,
                   description=f'Downloaded original file {batch.original_filename} from batch {batch.batch_id}')

        response = FileResponse(open(file_path, 'rb'), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{batch.original_filename}"'
        return response
