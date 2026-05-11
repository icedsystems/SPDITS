from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Partner, UserSession


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'partner', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'partner']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['email']
    fieldsets = UserAdmin.fieldsets + (
        ('SPDITS', {'fields': ('role', 'partner', 'supervisor', 'phone', 'azure_oid', 'is_invitation_accepted')}),
    )


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'contact_email', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'contact_email']


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'login_at', 'is_active']
    list_filter = ['is_active']
    search_fields = ['user__email']
    readonly_fields = ['user', 'session_key', 'ip_address', 'user_agent', 'login_at', 'last_activity']
