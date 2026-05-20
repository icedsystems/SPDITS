from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column
from apps.accounts.models import Partner, Role
from .models import Invitation


class InvitationCreateForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ['email', 'organization', 'partner', 'role', 'message']
        widgets = {'message': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('email'), Column('role')),
            Row(Column('organization'), Column('partner')),
            'message',
            Submit('submit', 'Send Invitation', css_class='btn btn-primary'),
        )

    def clean_email(self):
        from apps.accounts.models import CustomUser
        email = self.cleaned_data.get('email', '').strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                f'A user with the email address "{email}" already exists. '
                f'You cannot invite someone who already has an account.'
            )
        if Invitation.objects.filter(email__iexact=email, status='pending').exists():
            raise forms.ValidationError(
                f'A pending invitation has already been sent to "{email}". '
                f'Check the invitations list to resend or revoke it.'
            )
        return email


class InvitationAcceptForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput(), min_length=12)
    password_confirm = forms.CharField(widget=forms.PasswordInput(), label='Confirm Password')

    def clean_username(self):
        from apps.accounts.models import CustomUser
        username = self.cleaned_data.get('username', '').strip()
        if CustomUser.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                f'The username "{username}" is already taken. Please choose a different one.'
            )
        return username

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        pw_confirm = cleaned_data.get('password_confirm')
        if pw and pw_confirm and pw != pw_confirm:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data
