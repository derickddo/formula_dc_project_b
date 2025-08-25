import os
import hashlib
import hmac
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import transaction

from .models import Message
from .serializers import MessageSerializer
from .tasks import send_message_task
from django.conf import settings

# Get sender ID whitelist from environment variables
SENDER_ID_WHITELIST = os.environ.get('SMS_SENDER_ID_WHITELIST', '').split(',')

class MessageCreateView(APIView):
    """
    API endpoint to accept new messages.
    - Enforces idempotency via the 'Idempotency-Key' header.
    - Validates against a sender ID whitelist.
    - Creates a message record and enqueues it for sending.
    """
    def post(self, request, *args, **kwargs):
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key or not idempotency_key.startswith('send_msg:'):
            return Response(
                {"detail": "Missing or invalid Idempotency-Key header."},
                status=status.HTTP_400_BAD_REQUEST
            )

        client_message_id = idempotency_key.split(':', 1)[1]
        
        # Check for existing message with the same client_message_id
        # This is the core of the deduplication logic
        try:
            with transaction.atomic():
                existing_message = Message.objects.filter(client_message_id=client_message_id).first()
                if existing_message:
                    # Return the existing record to maintain idempotency
                    serializer = MessageSerializer(existing_message)
                    return Response(serializer.data, status=status.HTTP_200_OK)

                serializer = MessageSerializer(data=request.data)
                if not serializer.is_valid():
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                # Validate sender ID
                sender_id = serializer.validated_data['sender_id']
                print(SENDER_ID_WHITELIST)
                if sender_id not in SENDER_ID_WHITELIST:
                    return Response(
                        {"detail": "Invalid sender ID."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check for "STOP" keyword
                text = serializer.validated_data['text']
                if "STOP" in text.upper():
                    return Response(
                        {"detail": "Cannot send messages with 'STOP' keyword."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Set client_message_id before saving
                message = serializer.save(client_message_id=client_message_id)

                # Enqueue the message for sending
                print("ENQUEUED")
                send_message_task.delay(message.id)

                return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MessageDetailView(APIView):
    """
    API endpoint to retrieve a message by its ID.
    """
    def get(self, request, pk, *args, **kwargs):
        try:
            message = Message.objects.get(pk=pk)
            serializer = MessageSerializer(message)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Message.DoesNotExist:
            return Response(
                {"detail": "Message not found."},
                status=status.HTTP_404_NOT_FOUND
            )

class DlrWebhookView(APIView):
    """
    Webhook endpoint to receive Delivery Receipts from the provider.
    - Updates message status to DELIVERED or FAILED.
    - Note: This is where you would typically perform HMAC signature verification
    to ensure the request is from a trusted source.
    """
    # This helper method performs the signature validation.
    def is_valid_signature(self, request):
        try:
            # The signature is typically sent in a custom header
            received_signature = request.headers.get('X-Provider-Signature', '')
            
            # The canonical payload string for hashing, sorting keys is critical
            # Note: We use `request.body` here instead of `request.data` to get the raw string
            # and avoid any potential re-encoding issues
            body = request.body.decode('utf-8')
            
            # Use your secret key from settings
            secret = settings.SMS_WEBHOOK_SECRET.encode('utf-8')
            
            # Calculate the HMAC signature using SHA256
            calculated_signature = hmac.new(
                secret,
                body.encode('utf-8'),
                hashlib.sha256,
            ).hexdigest()

            print(calculated_signature)
            
            # Compare the signatures in a constant-time manner to prevent timing attacks
            return hmac.compare_digest(calculated_signature, received_signature)
        except (AttributeError, TypeError):
            # Handle cases where headers or data are missing or malformed
            return False


    def post(self, request, *args, **kwargs):
        # 1. Perform HMAC signature validation first.
        if not self.is_valid_signature(request):
            return Response(
                {"detail": "Invalid signature."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        provider_data = request.data
        provider_reference = provider_data.get('provider_reference')
        status_update = provider_data.get('status')
        
        if not all([provider_reference, status_update]):
            return Response(
                {"detail": "Missing required fields."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            message = Message.objects.get(provider_reference=provider_reference)
            if status_update.upper() == 'DELIVERED':
                message.status = 'DELIVERED'
                message.delivered_at = timezone.now()
            elif status_update.upper() == 'FAILED':
                message.status = 'FAILED'
            else:
                return Response(
                    {"detail": "Invalid status value."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            message.save()
            return Response({"detail": "DLR processed successfully."}, status=status.HTTP_200_OK)

        except Message.DoesNotExist:
            return Response(
                {"detail": "Message with provider reference not found."},
                status=status.HTTP_404_NOT_FOUND
            )


