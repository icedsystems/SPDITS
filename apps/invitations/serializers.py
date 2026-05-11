from rest_framework import serializers
from .models import Invitation


class InvitationSerializer(serializers.ModelSerializer):
    invited_by_name = serializers.CharField(source='invited_by.get_full_name', read_only=True)
    partner_name = serializers.CharField(source='partner.name', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invitation
        fields = [
            'id', 'email', 'organization', 'partner', 'partner_name',
            'role', 'invited_by', 'invited_by_name', 'status',
            'expiry_time', 'is_valid', 'created_at',
        ]
        read_only_fields = ['token', 'token_hash', 'created_at']
