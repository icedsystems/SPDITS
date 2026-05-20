from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'sftp'

urlpatterns = [
    path('', RedirectView.as_view(url='/sftp/config/', permanent=False)),
    path('logs/', views.SFTPLogListView.as_view(), name='log_list'),
    path('config/', views.SFTPConfigListView.as_view(), name='config_list'),
    path('config/new/', views.SFTPConfigCreateView.as_view(), name='config_create'),
    path('config/<int:pk>/edit/', views.SFTPConfigEditView.as_view(), name='config_edit'),
]
