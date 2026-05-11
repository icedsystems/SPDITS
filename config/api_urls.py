from django.urls import path, include

urlpatterns = [
    path('auth/', include('apps.accounts.api_urls')),
    path('invitations/', include('apps.invitations.api_urls')),
    path('uploads/', include('apps.uploads.api_urls')),
    path('sftp/', include('apps.sftp_ingestion.api_urls')),
    path('participants/', include('apps.participants.api_urls')),
    path('tracing/', include('apps.tracing.api_urls')),
    path('assignments/', include('apps.assignments.api_urls')),
    path('interviews/', include('apps.interviews.api_urls')),
    path('audit/', include('apps.audit.api_urls')),
]
