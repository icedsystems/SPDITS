from django.urls import path
from . import api_views

urlpatterns = [
    path('', api_views.AuditLogListAPIView.as_view()),
    path('feed/', api_views.AuditFeedAPIView.as_view()),
]
