import os
import math
import time
import uuid # <-- new import for generating mock provider reference
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.utils import timezone
from .models import Message

# Get DLR timeout from environment variables
DLR_TIMEOUT_MINUTES = int(os.environ.get('SMS_DLR_TIMEOUT_MINUTES', 5))

# Rate limit settings
MESSAGE_THROUGHPUT_PER_SECOND = 10  # N msg/sec
THROTTLING_DELAY_MS = 1000 / MESSAGE_THROUGHPUT_PER_SECOND # Delay in ms

@shared_task(bind=True, default_retry_delay=60, max_retries=5)
def send_message_task(self, message_id):
    """
    Celery task to handle sending a message with rate-limiting and retries.
    """
    # Simulate throughput windowing
    # This is a very simple form of rate limiting. A more robust solution
    # would use a distributed lock or a dedicated rate-limiting library.
    time.sleep(THROTTLING_DELAY_MS / 1000)

    try:
        message = Message.objects.get(id=message_id)

        # Simulate sending the message to an external provider
        # Here, you would replace this with actual API calls to an SMPP-style provider
        if message.status == 'INITIATED':
            print(f"Simulating sending message: {message_id}")
            
            # First, update the status to QUEUED as it's being processed
            message.status = 'QUEUED'
            message.sent_at = timezone.now()
            
            # Calculate encoding and segment count
            # A very basic calculation for demonstration
            if set(message.text) <= set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\r\n@£$¥èéùìòÇØøÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#%&'()*+,-./:;<=>?¡¿"):
                message.encoding = 'GSM-7'
                message.segment_count = math.ceil(len(message.text) / 160)
            else:
                message.encoding = 'UCS-2'
                message.segment_count = math.ceil(len(message.text) / 70)
            
            # Assign a mock provider reference
            message.provider_reference = "provider_ref_123"
            message.save()
            
            # Simulate a successful send, next status is 'SENT'
            message.status = 'SENT'
            message.save()

            print(f"Message {message.id} successfully sent with provider reference: {message.provider_reference}")
            return 'Message sent'
        
        else:
            # If the task is called for a message that has already been sent
            print(f"Message {message_id} already processed. Status: {message.status}")
            return 'Already processed'

    except Message.DoesNotExist:
        # Don't retry if the message object no longer exists
        print(f"Message with ID {message_id} does not exist.")
        return 'Message does not exist'

    except Exception as exc:
        # Retry with exponential backoff
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            print(f"Max retries exceeded for message {message_id}. Moving to DLQ.")
            # Move to Dead Letter Queue (DLQ)
            # This would involve a separate task or service to handle failures

@shared_task
def check_dlr_latency():
    """
    A periodic task to check for messages that have been SENT but not DELIVERED
    after a defined timeout.
    """
    timeout_threshold = timezone.now() - timezone.timedelta(minutes=DLR_TIMEOUT_MINUTES)
    
    overdue_messages = Message.objects.filter(
        status='SENT',
        sent_at__lte=timeout_threshold
    )

    if overdue_messages.exists():
        for message in overdue_messages:
            print(f"ALERT: DLR for message {message.id} is overdue. Sent at {message.sent_at}.")
            # You would typically trigger an alert here (e.g., email, PagerDuty, etc.)
            # For simplicity, we just print a message.
            # You could also move them to a 'SUSPENDED' or 'OVERDUE' status
            # to prevent them from being sent again.
    else:
        print("All SENT messages have a timely DLR.")