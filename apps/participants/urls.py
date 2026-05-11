from django.urls import path
from . import views

app_name = 'participants'

urlpatterns = [
    path('', views.ParticipantListView.as_view(), name='list'),
    path('<int:pk>/', views.ParticipantDetailView.as_view(), name='detail'),
    path('<int:pk>/reidentify/', views.ReIdentifyView.as_view(), name='reidentify'),
    path('export/', views.ParticipantExportView.as_view(), name='export'),
]
