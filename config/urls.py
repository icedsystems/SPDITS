from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView

admin.site.site_header = 'ICED SPDITS Administration'
admin.site.site_title = 'SPDITS Admin'
admin.site.index_title = 'System Administration'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('invitations/', include('apps.invitations.urls', namespace='invitations')),
    path('uploads/', include('apps.uploads.urls', namespace='uploads')),
    path('sftp/', include('apps.sftp_ingestion.urls', namespace='sftp')),
    path('participants/', include('apps.participants.urls', namespace='participants')),
    path('tracing/', include('apps.tracing.urls', namespace='tracing')),
    path('assignments/', include('apps.assignments.urls', namespace='assignments')),
    path('interviews/', include('apps.interviews.urls', namespace='interviews')),
    path('audit/', include('apps.audit.urls', namespace='audit')),
    path('compliance/', include('apps.compliance.urls', namespace='compliance')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('dashboard/', include('apps.dashboards.urls', namespace='dashboards')),
    path('api/v1/', include('config.api_urls')),
    path('manual/', TemplateView.as_view(template_name='manual/user_manual.html'), name='user_manual'),
    path('brochure/', TemplateView.as_view(template_name='manual/brochure.html'), name='brochure'),
    # Root redirect → dashboard
    path('', RedirectView.as_view(url='/dashboard/', permanent=False), name='home'),
]

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
