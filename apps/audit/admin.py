from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user_email', 'user_role', 'action', 'module', 'record_id', 'ip_address']
    list_filter = ['action', 'module', 'user_role']
    search_fields = ['user_email', 'action', 'description']
    readonly_fields = [f.name for f in AuditLog._meta.get_fields()]
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
