from django.urls import path
from . import api_views

urlpatterns = [
    path('', api_views.ParticipantListAPIView.as_view()),
    path('<int:pk>/', api_views.ParticipantDetailAPIView.as_view()),
]
