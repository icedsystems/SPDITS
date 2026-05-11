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

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'username', 'role', 'partner', 'supervisor', 'phone', 'password']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('first_name'), Column('last_name')),
            Row(Column('email'), Column('username')),
            Row(Column('role'), Column('partner')),
            Row(Column('supervisor'), Column('phone')),
            'password',
            Submit('submit', 'Create User', css_class='btn btn-primary'),
        )


class UserEditForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'role', 'partner', 'supervisor', 'phone', 'is_active']


class PartnerForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = ['name', 'code', 'contact_email', 'contact_name', 'phone', 'address', 'sftp_username', 'sftp_directory', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Save Partner', css_class='btn btn-primary'))
