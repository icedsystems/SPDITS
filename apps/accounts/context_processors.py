def user_role(request):
    if request.user.is_authenticated:
        ctx = {
            'user_role': request.user.role,
            'is_admin': request.user.is_admin(),
            'is_partner': request.user.is_partner(),
            'is_supervisor': request.user.is_supervisor(),
            'is_enumerator': request.user.is_enumerator(),
            'is_compliance_officer': request.user.is_compliance_officer(),
            'is_tracer': request.user.is_tracer(),
            'can_reidentify': request.user.can_reidentify(),
            'pending_approvals_count': 0,
        }
        if request.user.is_admin():
            try:
                from apps.uploads.models import UploadBatch, BatchStatus
                ctx['pending_approvals_count'] = UploadBatch.objects.filter(
                    status=BatchStatus.PENDING_APPROVAL
                ).count()
            except Exception:
                pass
        return ctx
    return {}
