from django.contrib import admin
from .models import Participant, IdentityMap, ReIdentificationLog


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['pseudo_code', 'partner', 'status', 'is_duplicate', 'created_at']
    list_filter = ['status', 'partner', 'is_duplicate']
    search_fields = ['pseudo_code']
    readonly_fields = ['pseudo_code', 'created_at', 'updated_at']


@admin.register(ReIdentificationLog)
class ReIdentificationLogAdmin(admin.ModelAdmin):
    list_display = ['participant', 'requested_by', 'reason', 'viewed_at']
    readonly_fields = ['participant', 'requested_by', 'reason', 'ip_address', 'viewed_at', 'fields_accessed']
