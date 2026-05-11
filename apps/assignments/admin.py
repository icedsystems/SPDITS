from django.contrib import admin
from .models import Assignment


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['participant', 'enumerator', 'supervisor', 'status', 'assigned_at']
    list_filter = ['status', 'supervisor']
    search_fields = ['participant__pseudo_code', 'enumerator__email']
