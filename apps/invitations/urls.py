from django.urls import path
from . import views

app_name = 'invitations'

urlpatterns = [
    path('', views.InvitationListView.as_view(), name='list'),
    path('create/', views.InvitationCreateView.as_view(), name='create'),
    path('<int:pk>/revoke/', views.InvitationRevokeView.as_view(), name='revoke'),
    path('accept/<str:token>/', views.InvitationAcceptView.as_view(), name='accept'),
]
