from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    SYSTEM_ADMIN = 'system_admin', _('System Admin')
    IMPLEMENTING_PARTNER = 'implementing_partner', _('Implementing Partner')
    SUPERVISOR = 'supervisor', _('Supervisor')
    ENUMERATOR = 'enumerator', _('Enumerator')
    COMPLIANCE_OFFICER = 'compliance_officer', _('Compliance Officer')
    TRACER = 'tracer', _('Tracer')


class Partner(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    contact_email = models.EmailField()
    contact_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sftp_username = models.CharField(max_length=100, blank=True)
    sftp_directory = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50, choices=Role.choices, default=Role.ENUMERATOR)
    partner = models.ForeignKey(
        Partner, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='users'
    )
    supervisor = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='enumerators', limit_choices_to={'role': Role.SUPERVISOR}
    )
    phone = models.CharField(max_length=50, blank=True)
    is_invitation_accepted = models.BooleanField(default=False)
    azure_oid = models.CharField(max_length=255, blank=True, db_index=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    force_password_change = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    @property
    def display_role(self):
        return self.get_role_display()

    def has_role(self, *roles):
        """True if user's primary role OR any extra role is in the given roles."""
        if self.role in roles:
            return True
        return self.extra_role_assignments.filter(role__in=roles).exists()

    def get_all_roles(self):
        """Return list of all role values this user holds (primary + extra)."""
        roles = [self.role]
        for r in self.extra_role_assignments.values_list('role', flat=True):
            if r not in roles:
                roles.append(r)
        return roles

    def get_all_role_labels(self):
        role_map = dict(Role.choices)
        return [role_map.get(r, r) for r in self.get_all_roles()]

    def is_admin(self):
        return self.has_role(Role.SYSTEM_ADMIN)

    def is_partner(self):
        return self.has_role(Role.IMPLEMENTING_PARTNER)

    def is_supervisor(self):
        return self.has_role(Role.SUPERVISOR)

    def is_enumerator(self):
        return self.has_role(Role.ENUMERATOR)

    def is_compliance_officer(self):
        return self.has_role(Role.COMPLIANCE_OFFICER)

    def is_tracer(self):
        return self.has_role(Role.TRACER)

    def can_reidentify(self):
        return self.has_role(Role.SYSTEM_ADMIN, Role.COMPLIANCE_OFFICER)

    def can_approve_uploads(self):
        return self.has_role(Role.SYSTEM_ADMIN)

    def can_view_contacts(self):
        """Tracers, supervisors, and admins can view decrypted participant contacts."""
        return self.has_role(Role.SYSTEM_ADMIN, Role.SUPERVISOR, Role.TRACER)

    def get_role_badge_color(self):
        colors = {
            Role.SYSTEM_ADMIN: 'danger',
            Role.IMPLEMENTING_PARTNER: 'primary',
            Role.SUPERVISOR: 'warning',
            Role.ENUMERATOR: 'info',
            Role.COMPLIANCE_OFFICER: 'dark',
            Role.TRACER: 'success',
        }
        return colors.get(self.role, 'secondary')


class UserRole(models.Model):
    """Extra roles assigned to a user in addition to their primary role."""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='extra_role_assignments')
    role = models.CharField(max_length=50, choices=Role.choices)

    class Meta:
        unique_together = [('user', 'role')]
        verbose_name = 'Extra User Role'
        verbose_name_plural = 'Extra User Roles'

    def __str__(self):
        return f"{self.user.email} — {self.get_role_display()}"


class UserSession(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    login_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    logout_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-login_at']

    def __str__(self):
        return f"{self.user.email} — {self.login_at}"
