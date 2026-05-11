from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('oauth/init/', views.AzureOAuthInitView.as_view(), name='oauth_init'),
    path('oauth/callback/', views.AzureOAuthCallbackView.as_view(), name='oauth_callback'),
    path('profile/', views.profile_view, name='profile'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/edit/', views.UserEditView.as_view(), name='user_edit'),
    path('partners/', views.PartnerListView.as_view(), name='partner_list'),
    path('partners/create/', views.PartnerCreateView.as_view(), name='partner_create'),
    path('partners/<int:pk>/edit/', views.PartnerEditView.as_view(), name='partner_edit'),
]
