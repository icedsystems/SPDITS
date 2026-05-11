from django.contrib import admin
from .models import TracingLog


@admin.register(TracingLog)
class TracingLogAdmin(admin.ModelAdmin):
    list_display = ['participant', 'previous_status', 'new_status', 'updated_by', 'created_at']
    list_filter = ['new_status']
    search_fields = ['participant__pseudo_code']
    readonly_fields = ['created_at']
