from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('', views.AuditLogListView.as_view(), name='list'),
    path('dashboard/', views.AuditDashboardView.as_view(), name='dashboard'),
    path('<int:pk>/', views.AuditLogDetailView.as_view(), name='detail'),
    path('export/', views.AuditLogExportView.as_view(), name='export'),
    path('user/<int:user_id>/', views.UserTimelineView.as_view(), name='user_timeline'),
]
