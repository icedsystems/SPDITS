from django.urls import path
from . import api_views

urlpatterns = [
    path('', api_views.TracingLogListAPIView.as_view()),
    path('<int:participant_pk>/', api_views.ParticipantTracingLogAPIView.as_view()),
]
