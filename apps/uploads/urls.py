from django.urls import path
from . import views

app_name = 'uploads'

urlpatterns = [
    path('', views.UploadListView.as_view(), name='list'),
    path('new/', views.UploadCreateView.as_view(), name='create'),
    path('<int:pk>/', views.UploadDetailView.as_view(), name='detail'),
    path('<int:pk>/approve/', views.UploadApprovalView.as_view(), name='approve'),
    path('pending/', views.UploadPendingView.as_view(), name='pending'),
]
