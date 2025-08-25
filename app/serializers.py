from rest_framework import serializers
from .models import Message

class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for the Message model.
    """
    class Meta:
        model = Message
        fields = ['id', 'client_message_id', 'provider_reference', 'sender_id', 'recipient', 'text', 'status', 'encoding', 'segment_count', 'created_at']
        read_only_fields = ['id', 'status', 'provider_reference', 'encoding', 'client_message_id', 'segment_count', 'created_at']

