from django.urls import path
from . import api_views

urlpatterns = [
    path('logs/', api_views.SFTPLogListAPIView.as_view()),
]
