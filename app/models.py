import uuid
from django.db import models

# GSM-7 and UCS-2 encoding support
MESSAGE_ENCODING_CHOICES = [
    ('GSM-7', 'GSM-7'),
    ('UCS-2', 'UCS-2'),
]

# Message status tracking
MESSAGE_STATUS_CHOICES = [
    ('INITIATED', 'Initiated'),
    ('QUEUED', 'Queued'),
    ('SENT', 'Sent'),
    ('DELIVERED', 'Delivered'),
    ('FAILED', 'Failed'),
]

class Message(models.Model):
    """
    Represents an outgoing message in the system.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_message_id = models.CharField(max_length=255, unique=True, db_index=True)
    sender_id = models.CharField(max_length=11)
    recipient = models.CharField(max_length=15)
    text = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=MESSAGE_STATUS_CHOICES,
        default='INITIATED'
    )
    encoding = models.CharField(
        max_length=5,
        choices=MESSAGE_ENCODING_CHOICES,
        default='GSM-7'
    )
    provider_reference = models.CharField(max_length=255, blank=True)
    segment_count = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Message to {self.recipient} (Status: {self.status})"

