from django.urls import path
from . import api_views

urlpatterns = [
    path('', api_views.InvitationListAPIView.as_view(), name='api_invitation_list'),
    path('<int:pk>/', api_views.InvitationDetailAPIView.as_view(), name='api_invitation_detail'),
]
