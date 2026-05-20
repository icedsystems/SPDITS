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
    password = forms.CharField(widget=forms.PasswordInput(), required=False,
                                help_text='Leave blank for Microsoft OAuth users.')
    extra_roles = forms.MultipleChoiceField(
        choices=Role.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Additional Roles',
        help_text='Assign extra roles alongside the primary role above.',
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'username', 'role', 'partner', 'supervisor', 'phone', 'password']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False


class UserEditForm(forms.ModelForm):
    extra_roles = forms.MultipleChoiceField(
        choices=Role.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Additional Roles',
        help_text='Assign extra roles alongside the primary role above.',
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'role', 'partner', 'supervisor', 'phone', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        fields = ['name', 'code', 'contact_email', 'contact_name', 'phone', 'address', 'sftp_username', 'sftp_directory', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Save Partner', css_class='btn btn-primary'))
