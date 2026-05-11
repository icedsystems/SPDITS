import logging
import urllib.parse
import msal
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DetailView

from apps.audit.utils import log_action
from .forms import CustomLoginForm, UserCreateForm, UserEditForm, PartnerForm
from .models import CustomUser, Partner

logger = logging.getLogger(__name__)


class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboards:home')
        form = CustomLoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', 'dashboards:home')
            return redirect(next_url)
        return render(request, self.template_name, {'form': form})


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('accounts:login')


class AzureOAuthInitView(View):
    """Redirect user to Microsoft login."""
    def get(self, request):
        authority = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}"
        msal_app = msal.ConfidentialClientApplication(
            settings.AZURE_AD_CLIENT_ID,
            authority=authority,
            client_credential=settings.AZURE_AD_CLIENT_SECRET,
        )
        auth_url = msal_app.get_authorization_request_url(
            scopes=['User.Read'],
            redirect_uri=settings.AZURE_AD_REDIRECT_URI,
            state=request.session.session_key,
        )
        return redirect(auth_url)


class AzureOAuthCallbackView(View):
    """Handle Microsoft OAuth callback."""
    def get(self, request):
        code = request.GET.get('code')
        error = request.GET.get('error')
        if error:
            messages.error(request, f'Microsoft login failed: {error}')
            return redirect('accounts:login')

        authority = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}"
        msal_app = msal.ConfidentialClientApplication(
            settings.AZURE_AD_CLIENT_ID,
            authority=authority,
            client_credential=settings.AZURE_AD_CLIENT_SECRET,
        )
        result = msal_app.acquire_token_by_authorization_code(
            code,
            scopes=['User.Read'],
            redirect_uri=settings.AZURE_AD_REDIRECT_URI,
        )
        if 'error' in result:
            messages.error(request, 'Could not authenticate with Microsoft.')
            return redirect('accounts:login')

        claims = result.get('id_token_claims', {})
        azure_oid = claims.get('oid', '')
        email = claims.get('preferred_username', claims.get('email', ''))
        name_parts = claims.get('name', '').split(' ', 1)

        try:
            user = CustomUser.objects.get(azure_oid=azure_oid)
        except CustomUser.DoesNotExist:
            try:
                user = CustomUser.objects.get(email=email)
                user.azure_oid = azure_oid
                user.save(update_fields=['azure_oid'])
            except CustomUser.DoesNotExist:
                messages.error(request, 'No account found. Please request an invitation from your administrator.')
                return redirect('accounts:login')

        if not user.is_active:
            messages.error(request, 'Your account is inactive.')
            return redirect('accounts:login')

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('dashboards:home')


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_admin()


class UserListView(AdminRequiredMixin, ListView):
    model = CustomUser
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('partner')
        q = self.request.GET.get('q')
        role = self.request.GET.get('role')
        if q:
            qs = qs.filter(email__icontains=q) | qs.filter(first_name__icontains=q) | qs.filter(last_name__icontains=q)
        if role:
            qs = qs.filter(role=role)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['roles'] = CustomUser.role.field.choices
        return ctx


class UserCreateView(AdminRequiredMixin, CreateView):
    model = CustomUser
    form_class = UserCreateForm
    template_name = 'accounts/user_form.html'
    success_url = '/accounts/users/'

    def form_valid(self, form):
        user = form.save(commit=False)
        password = form.cleaned_data.get('password')
        if password:
            user.set_password(password)
        user.save()
        log_action(self.request, 'CREATE_USER', 'accounts', user.pk, description=f'Created user {user.email}')
        messages.success(self.request, f'User {user.email} created successfully.')
        return redirect(self.success_url)


class UserEditView(AdminRequiredMixin, UpdateView):
    model = CustomUser
    form_class = UserEditForm
    template_name = 'accounts/user_form.html'
    success_url = '/accounts/users/'

    def form_valid(self, form):
        user = form.save()
        log_action(self.request, 'EDIT_USER', 'accounts', user.pk, description=f'Edited user {user.email}')
        messages.success(self.request, 'User updated successfully.')
        return redirect(self.success_url)


class PartnerListView(AdminRequiredMixin, ListView):
    model = Partner
    template_name = 'accounts/partner_list.html'
    context_object_name = 'partners'
    paginate_by = 25


class PartnerCreateView(AdminRequiredMixin, CreateView):
    model = Partner
    form_class = PartnerForm
    template_name = 'accounts/partner_form.html'
    success_url = '/accounts/partners/'

    def form_valid(self, form):
        partner = form.save()
        log_action(self.request, 'CREATE_PARTNER', 'accounts', partner.pk, description=f'Created partner {partner.name}')
        messages.success(self.request, f'Partner {partner.name} created.')
        return redirect(self.success_url)


class PartnerEditView(AdminRequiredMixin, UpdateView):
    model = Partner
    form_class = PartnerForm
    template_name = 'accounts/partner_form.html'
    success_url = '/accounts/partners/'


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'user': request.user})
