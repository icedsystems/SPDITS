from django.urls import path
from . import views

app_name = 'tracing'

urlpatterns = [
    path('', views.TracingQueueView.as_view(), name='queue'),
    path('traced/', views.TracedQueueView.as_view(), name='traced_queue'),
    path('<int:pk>/update/', views.TracingUpdateView.as_view(), name='update'),
    path('<int:participant_pk>/history/', views.TracingHistoryView.as_view(), name='history'),
]
