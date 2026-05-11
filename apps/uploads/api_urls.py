from django.urls import path
from . import api_views

urlpatterns = [
    path('', api_views.UploadBatchListAPIView.as_view()),
    path('<int:pk>/', api_views.UploadBatchDetailAPIView.as_view()),
]
