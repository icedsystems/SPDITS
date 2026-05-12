from django.urls import path
from . import views

app_name = 'assignments'

urlpatterns = [
    path('', views.AssignmentListView.as_view(), name='list'),
    path('queue/', views.AssignmentQueueView.as_view(), name='queue'),
    path('bulk-assign/', views.BulkAssignView.as_view(), name='bulk_assign'),
    path('mine/', views.MyAssignmentsView.as_view(), name='mine'),
    path('export/<int:enumerator_pk>/', views.AssignmentExportView.as_view(), name='export'),
    path('download/<uuid:token>/', views.SecureCSVDownloadView.as_view(), name='download_csv'),
]
