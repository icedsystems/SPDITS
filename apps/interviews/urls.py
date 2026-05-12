from django.urls import path
from . import views

app_name = 'interviews'

urlpatterns = [
    path('', views.InterviewListView.as_view(), name='list'),
    path('<int:pk>/', views.InterviewDetailView.as_view(), name='detail'),
    path('<int:pk>/update/', views.InterviewUpdateView.as_view(), name='update'),
    path('create/<int:participant_pk>/', views.InterviewCreateView.as_view(), name='create'),
    path('quick/<int:assignment_pk>/', views.QuickInterviewUpdateView.as_view(), name='quick_update'),
]
