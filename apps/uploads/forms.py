from django import forms
from django.conf import settings
from .models import UploadBatch


class FileUploadForm(forms.Form):
    partner = forms.ModelChoiceField(
        queryset=None,
        empty_label='Select Partner',
    )
    file = forms.FileField(
        widget=forms.FileInput(attrs={'accept': '.csv,.xls,.xlsx', 'class': 'form-control'}),
        help_text='Accepted formats: CSV, XLS, XLSX. Max size: 100 MB.'
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        from apps.accounts.models import Partner
        if user and user.is_partner() and user.partner:
            self.fields['partner'].queryset = Partner.objects.filter(pk=user.partner.pk)
            self.fields['partner'].initial = user.partner
        else:
            self.fields['partner'].queryset = Partner.objects.filter(is_active=True)

    def clean_file(self):
        f = self.cleaned_data['file']
        if f.size > settings.MAX_UPLOAD_SIZE:
            raise forms.ValidationError(f'File too large. Maximum size is {settings.MAX_UPLOAD_SIZE // (1024*1024)} MB.')
        ext = '.' + f.name.rsplit('.', 1)[-1].lower()
        if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
            raise forms.ValidationError(f'Invalid file type. Allowed: CSV, XLS, XLSX.')
        return f


class UploadApprovalForm(forms.Form):
    action = forms.ChoiceField(choices=[('approve', 'Approve'), ('reject', 'Reject')])
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label='Review Notes'
    )
