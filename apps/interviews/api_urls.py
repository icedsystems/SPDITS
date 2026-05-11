from django.urls import path
from . import api_views

urlpatterns = [
    path('', api_views.InterviewListAPIView.as_view()),
    path('<int:pk>/', api_views.InterviewDetailAPIView.as_view()),
]
