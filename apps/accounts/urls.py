from django.contrib.auth import views as auth_views
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
    path('users/<int:pk>/reset-password/', views.AdminPasswordResetView.as_view(), name='admin_reset_password'),
    path('set-password/', views.SetPasswordView.as_view(), name='set_password'),
    path('partners/', views.PartnerListView.as_view(), name='partner_list'),
    path('partners/create/', views.PartnerCreateView.as_view(), name='partner_create'),
    path('partners/<int:pk>/edit/', views.PartnerEditView.as_view(), name='partner_edit'),
    # Self-service password reset (Django built-in, uses Graph email backend)
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/password_reset_email.html',
             subject_template_name='accounts/password_reset_subject.txt',
             success_url='/accounts/password-reset/done/',
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html',
         ),
         name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             success_url='/accounts/password-reset/complete/',
         ),
         name='password_reset_confirm'),
    path('password-reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html',
         ),
         name='password_reset_complete'),
]
