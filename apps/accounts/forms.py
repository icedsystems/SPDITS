from django import forms
from django.contrib.auth.forms import AuthenticationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field
from .models import CustomUser, Partner, Role


class CustomLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your@email.com', 'autofocus': True})
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••••••'})
    )


class UserCreateForm(forms.ModelForm):
    extra_roles = forms.MultipleChoiceField(
        choices=Role.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Additional Roles',
        help_text='Assign extra roles alongside the primary role above.',
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'username', 'role', 'partner', 'supervisor', 'phone']

    def __init__(self, *args, **kwargs):
        self.supervisor_mode = kwargs.pop('supervisor_mode', False)
        self.supervisor_user = kwargs.pop('supervisor_user', None)
        super().__init__(*args, **kwargs)
        if self.supervisor_mode:
            # Supervisors only create enumerators — hide admin-only fields
            for f in ['role', 'supervisor', 'username', 'extra_roles']:
                self.fields.pop(f, None)
            # Limit partner choices to the supervisor's assigned partners
            if self.supervisor_user:
                assigned = self.supervisor_user.get_assigned_partners()
                if assigned.count() == 1:
                    # Single partner — hide the field, set as initial
                    self.fields.pop('partner', None)
                    self._single_partner = assigned.first()
                else:
                    self.fields['partner'].queryset = assigned
                    self.fields['partner'].required = True
                    self.fields['partner'].empty_label = 'Select partner…'
            else:
                self.fields.pop('partner', None)
        self.helper = FormHelper()
        self.helper.form_tag = False

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                f'A user with the email address "{email}" already exists in the system.'
            )
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if username and CustomUser.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                f'The username "{username}" is already taken. Please choose a different one.'
            )
        return username


class UserEditForm(forms.ModelForm):
    extra_roles = forms.MultipleChoiceField(
        choices=Role.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Additional Roles',
        help_text='Assign extra roles alongside the primary role above.',
    )
    extra_partners = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Additional Partners',
        help_text='Extra implementing partners this supervisor can work across.',
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'role', 'partner', 'supervisor', 'phone', 'is_active', 'extra_partners']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Partner
        self.fields['extra_partners'].queryset = Partner.objects.filter(is_active=True).order_by('name')
        if self.instance and self.instance.pk:
            current_extra = list(
                self.instance.extra_role_assignments.values_list('role', flat=True)
            )
            self.fields['extra_roles'].initial = current_extra
        self.helper = FormHelper()
        self.helper.form_tag = False


class PartnerForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = ['name', 'code', 'contact_email', 'contact_name', 'phone', 'address', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Save Partner', css_class='btn btn-primary'))
