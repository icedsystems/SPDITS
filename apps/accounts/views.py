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
from .models import CustomUser, Partner, UserRole

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


class AdminOrSupervisorMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_admin() or self.request.user.is_supervisor()


class UserListView(AdminOrSupervisorMixin, ListView):
    model = CustomUser
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user
        if user.is_admin():
            qs = CustomUser.objects.select_related('partner').all()
            q = self.request.GET.get('q')
            role = self.request.GET.get('role')
            if q:
                qs = qs.filter(email__icontains=q) | qs.filter(first_name__icontains=q) | qs.filter(last_name__icontains=q)
            if role:
                qs = qs.filter(role=role)
        else:
            # Supervisors see only their own enumerators
            from .models import Role
            qs = CustomUser.objects.select_related('partner').filter(
                role=Role.ENUMERATOR, supervisor=user
            )
            q = self.request.GET.get('q')
            if q:
                qs = qs.filter(email__icontains=q) | qs.filter(first_name__icontains=q) | qs.filter(last_name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['roles'] = CustomUser.role.field.choices
        ctx['is_supervisor_view'] = self.request.user.is_supervisor() and not self.request.user.is_admin()
        return ctx


class UserCreateView(AdminOrSupervisorMixin, CreateView):
    model = CustomUser
    form_class = UserCreateForm
    template_name = 'accounts/user_form.html'
    success_url = '/accounts/users/'

    def _is_supervisor_mode(self):
        return self.request.user.is_supervisor() and not self.request.user.is_admin()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['supervisor_mode'] = self._is_supervisor_mode()
        if self._is_supervisor_mode():
            kwargs['supervisor_user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['supervisor_mode'] = self._is_supervisor_mode()
        if self._is_supervisor_mode():
            ctx['supervisor_partner_count'] = self.request.user.get_assigned_partners().count()
        return ctx

    def form_valid(self, form):
        import secrets
        from .models import Role
        user = form.save(commit=False)
        user.set_password(secrets.token_urlsafe(20))
        user.force_password_change = True
        if self._is_supervisor_mode():
            user.role = Role.ENUMERATOR
            user.supervisor = self.request.user
            # Partner: either chosen from form or auto from single-partner supervisor
            if 'partner' not in form.cleaned_data:
                user.partner = getattr(form, '_single_partner', None) or self.request.user.partner
            else:
                user.partner = form.cleaned_data.get('partner') or self.request.user.partner
        user.save()
        if self.request.user.is_admin():
            extra_roles = form.cleaned_data.get('extra_roles', [])
            UserRole.objects.filter(user=user).delete()
            for role in extra_roles:
                if role != user.role:
                    UserRole.objects.get_or_create(user=user, role=role)
        log_action(self.request, 'CREATE_USER', 'accounts', user.pk, description=f'Created user {user.email}')
        # Send welcome email so the new user knows they have an account and how to log in
        try:
            from django.core.mail import send_mail
            from django.template.loader import render_to_string
            request = self.request
            login_url = request.build_absolute_uri('/accounts/login/')
            ctx = {'user': user, 'login_url': login_url}
            send_mail(
                subject='[ICED SPDITS] Your account has been created',
                message=render_to_string('emails/welcome_user.txt', ctx),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=render_to_string('emails/welcome_user.html', ctx),
                fail_silently=False,
            )
            messages.success(self.request, f'User {user.get_full_name()} created and a welcome email has been sent to {user.email}.')
        except Exception as e:
            logger.exception(f'Welcome email failed for {user.email}: {e}')
            messages.warning(self.request, f'User {user.get_full_name()} created, but the welcome email could not be sent ({e}). Please share the login link manually: /accounts/login/')
        return redirect(self.success_url)


class UserEditView(AdminRequiredMixin, UpdateView):
    model = CustomUser
    form_class = UserEditForm
    template_name = 'accounts/user_form.html'
    success_url = '/accounts/users/'

    def form_valid(self, form):
        user = form.save(commit=False)
        user.save()
        # Extra roles
        extra_roles = form.cleaned_data.get('extra_roles', [])
        UserRole.objects.filter(user=user).delete()
        for role in extra_roles:
            if role != user.role:
                UserRole.objects.get_or_create(user=user, role=role)
        # Extra partners (M2M — must save after user.save())
        extra_partners = form.cleaned_data.get('extra_partners', [])
        user.extra_partners.set(extra_partners)
        log_action(self.request, 'EDIT_USER', 'accounts', user.pk, description=f'Edited user {user.email}')
        messages.success(self.request, 'User updated successfully.')
        return redirect(self.success_url)


class SetPasswordView(LoginRequiredMixin, View):
    """Shown to users with force_password_change=True. Must complete before accessing anything."""
    template_name = 'accounts/set_password.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        p1 = request.POST.get('new_password1', '').strip()
        p2 = request.POST.get('new_password2', '').strip()
        if not p1 or len(p1) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
            return render(request, self.template_name)
        if p1 != p2:
            messages.error(request, 'Passwords do not match.')
            return render(request, self.template_name)
        request.user.set_password(p1)
        request.user.force_password_change = False
        request.user.save(update_fields=['password', 'force_password_change'])
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        log_action(request, 'SET_OWN_PASSWORD', 'accounts', request.user.pk,
                   description=f'{request.user.email} set their own password on first login')
        messages.success(request, 'Password set successfully. Welcome to ICED SPDITS.')
        return redirect('dashboards:home')


class AdminPasswordResetView(AdminRequiredMixin, View):
    """Flag user for forced password reset on next login — admin sets no password."""

    def post(self, request, pk):
        import secrets
        user = get_object_or_404(CustomUser, pk=pk)
        user.set_password(secrets.token_urlsafe(20))
        user.force_password_change = True
        user.save(update_fields=['password', 'force_password_change'])
        log_action(request, 'ADMIN_PASSWORD_RESET', 'accounts', pk,
                   description=f'{request.user.email} triggered forced password reset for {user.email}')
        messages.success(request, f'{user.get_full_name()} will be prompted to set a new password on their next login.')
        return redirect('accounts:user_list')


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
