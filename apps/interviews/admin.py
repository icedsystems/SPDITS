from django.contrib import admin
from .models import Interview, InterviewStatusHistory


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ['participant', 'enumerator', 'status', 'scheduled_date', 'created_at']
    list_filter = ['status']
    search_fields = ['participant__pseudo_code']


@admin.register(InterviewStatusHistory)
class InterviewStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['interview', 'previous_status', 'new_status', 'changed_by', 'changed_at']
    readonly_fields = ['changed_at']
