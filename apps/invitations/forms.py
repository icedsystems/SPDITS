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


class InvitationAcceptForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput(), min_length=12)
    password_confirm = forms.CharField(widget=forms.PasswordInput(), label='Confirm Password')

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        pw_confirm = cleaned_data.get('password_confirm')
        if pw and pw_confirm and pw != pw_confirm:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data
