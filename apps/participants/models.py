from django.db import models
from cryptography.fernet import Fernet
from django.conf import settings
import base64


def get_fernet():
    key = settings.FIELD_ENCRYPTION_KEY
    if not key:
        key = Fernet.generate_key().decode()
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


class ParticipantStatus(models.TextChoices):
    UPLOADED = 'uploaded', 'Uploaded'
    TRACING = 'tracing', 'Tracing'
    TRACED = 'traced', 'Traced'
    ASSIGNED = 'assigned', 'Assigned'
    INTERVIEWED = 'interviewed', 'Interviewed'
    CLOSED = 'closed', 'Closed'


class Participant(models.Model):
    pseudo_code = models.CharField(max_length=50, unique=True, db_index=True)
    partner = models.ForeignKey('accounts.Partner', on_delete=models.PROTECT, related_name='participants')
    upload_batch = models.ForeignKey(
        'uploads.UploadBatch', on_delete=models.SET_NULL, null=True, blank=True, related_name='participants'
    )
    status = models.CharField(max_length=30, choices=ParticipantStatus.choices, default=ParticipantStatus.UPLOADED)
    data = models.JSONField(default=dict, help_text='Non-sensitive participant data (quasi-identifiers)')
    row_number = models.IntegerField(default=0, help_text='Original row number in uploaded file')
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    is_valid = models.BooleanField(default=True)
    validation_errors = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['pseudo_code']
        verbose_name = 'Participant'
        verbose_name_plural = 'Participants'

    def __str__(self):
        return self.pseudo_code

    def get_status_badge(self):
        colors = {
            ParticipantStatus.UPLOADED: 'secondary',
            ParticipantStatus.TRACING: 'warning',
            ParticipantStatus.TRACED: 'info',
            ParticipantStatus.ASSIGNED: 'primary',
            ParticipantStatus.INTERVIEWED: 'success',
            ParticipantStatus.CLOSED: 'dark',
        }
        return colors.get(self.status, 'secondary')

    def get_display_data(self):
        """Return safe quasi-identifier fields for display."""
        safe_fields = ['age', 'birth_year', 'county', 'gender', 'sub_county', 'ward']
        return {k: v for k, v in self.data.items() if k.lower() in safe_fields}


class IdentityMap(models.Model):
    """Encrypted mapping of participant pseudocode to direct identifiers."""
    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name='identity_map')
    encrypted_name = models.BinaryField(null=True, blank=True)
    encrypted_national_id = models.BinaryField(null=True, blank=True)
    encrypted_passport = models.BinaryField(null=True, blank=True)
    encrypted_phone = models.BinaryField(null=True, blank=True)
    encrypted_alt_phone = models.BinaryField(null=True, blank=True)
    encrypted_email = models.BinaryField(null=True, blank=True)
    encrypted_address = models.BinaryField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def encrypt(self, value):
        if not value:
            return None
        f = get_fernet()
        return f.encrypt(str(value).encode())

    def decrypt(self, value):
        if not value:
            return None
        f = get_fernet()
        return f.decrypt(bytes(value)).decode()

    def set_identifiers(self, data: dict):
        self.encrypted_name = self.encrypt(data.get('name') or data.get('full_name'))
        self.encrypted_national_id = self.encrypt(data.get('national_id') or data.get('id_number'))
        self.encrypted_passport = self.encrypt(data.get('passport'))
        self.encrypted_phone = self.encrypt(data.get('phone') or data.get('phone_number'))
        self.encrypted_alt_phone = self.encrypt(data.get('alt_phone') or data.get('alternative_phone'))
        self.encrypted_email = self.encrypt(data.get('email'))
        self.encrypted_address = self.encrypt(data.get('address') or data.get('exact_address'))

    def get_identifiers(self):
        return {
            'name': self.decrypt(self.encrypted_name),
            'national_id': self.decrypt(self.encrypted_national_id),
            'passport': self.decrypt(self.encrypted_passport),
            'phone': self.decrypt(self.encrypted_phone),
            'alt_phone': self.decrypt(self.encrypted_alt_phone),
            'email': self.decrypt(self.encrypted_email),
            'address': self.decrypt(self.encrypted_address),
        }


class ReIdentificationLog(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='reidentification_logs')
    requested_by = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    reason = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    session_id = models.CharField(max_length=40, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)
    fields_accessed = models.JSONField(default=list)

    class Meta:
        ordering = ['-viewed_at']

    def __str__(self):
        return f"{self.requested_by.email} re-identified {self.participant.pseudo_code}"
