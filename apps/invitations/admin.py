from django.contrib import admin
from .models import Invitation


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ['email', 'role', 'status', 'invited_by', 'expiry_time', 'created_at']
    list_filter = ['status', 'role']
    search_fields = ['email', 'organization']
    readonly_fields = ['token', 'token_hash', 'created_at']
