import json
import hmac
import hashlib
import pytest
from django.conf import settings
from django.urls import reverse
from app.models import Message

# Use the Django test client to make requests
# It's a fixture provided by pytest-django
def test_send_message_deduplication(client, mocker):
    """
    Unit test to verify that the API endpoint correctly handles duplicate
    requests, ensuring only a single Message object is created.
    
    This tests the idempotency of the send_message endpoint.
    """
    url = reverse('send_message')
    recipient = "+1234567890"
    text = "Hello, idempotency!"
    client_request_id = "test-unique-id-123"

    # Mock the Celery task so we don't actually run it
    mocker.patch('app.tasks.send_message_task.delay')
    
    # 1. First request should succeed and create a message
    response_1 = client.post(
        url,
        json.dumps({
            "recipient": recipient,
            "text": text,
            "client_request_id": client_request_id
        }),
        content_type="application/json"
    )
    assert response_1.status_code == 202
    assert response_1.json()['status'] == 'QUEUED'

    # Check that one message was created in the database
    assert Message.objects.count() == 1
    assert Message.objects.first().client_request_id == client_request_id

    # 2. Second request with the same unique ID should also succeed,
    # but not create a new message
    response_2 = client.post(
        url,
        json.dumps({
            "recipient": recipient,
            "text": text,
            "client_request_id": client_request_id
        }),
        content_type="application/json"
    )
    assert response_2.status_code == 202
    
    # The message count should still be 1
    assert Message.objects.count() == 1

@pytest.mark.django_db
def test_dlr_webhook_valid_signature(client, mocker):
    """
    Unit test for the DLR webhook to ensure it accepts requests with
    a valid HMAC-SHA256 signature.
    
    This is a critical security test.
    """
    url = reverse('dlr_webhook')
    
    # Mock the secret key and DLR processing task
    mocker.patch('django.conf.settings.WEBHOOK_SECRET_KEY', 'my_secret_key')
    mocker.patch('messaging_app.tasks.process_dlr.delay')
    
    # Create a test payload and generate a valid signature
    payload = {
        "provider_reference": "provider_ref_123",
        "status": "DELIVERED"
        
    }
    payload_bytes = json.dumps(payload).encode('utf-8')
    signature = hmac.new(
        settings.WEBHOOK_SECRET_KEY.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    # Send the request with the valid signature
    headers = {'X-Provider-Signature': signature}
    response = client.post(
        url,
        payload_bytes,
        content_type="application/json",
        HTTP_X_SIGNATURE=signature
    )

    assert response.status_code == 200
    assert response.json()['status'] == 'success'
    
@pytest.mark.django_db
def test_dlr_webhook_invalid_signature(client, mocker):
    """
    Unit test for the DLR webhook to ensure it rejects requests with
    an invalid or missing signature.
    """
    url = reverse('dlr_webhook')
    
    # Mock the secret key
    mocker.patch('django.conf.settings.WEBHOOK_SECRET_KEY', 'my_secret_key')
    
    # Create a test payload but provide an invalid signature
    payload = {
        "provider_reference": "provider_ref_123",
        "status": "DELIVERED"
    }
    payload_bytes = json.dumps(payload).encode('utf-8')
    invalid_signature = "thisisnota-valid-signature"
    
    # Send the request with the invalid signature
    response = client.post(
        url,
        payload_bytes,
        content_type="application/json",
        HTTP_X_SIGNATURE=invalid_signature
    )
    
    assert response.status_code == 403 # Forbidden
    
@pytest.mark.django_db
def test_dlr_webhook_missing_signature(client, mocker):
    """
    Unit test for the DLR webhook to ensure it rejects requests with
    a missing signature header.
    """
    url = reverse('dlr-webhook')
    
    # Mock the secret key
    mocker.patch('django.conf.settings.WEBHOOK_SECRET_KEY', 'my_secret_key')
    
    # Create a test payload but with no signature header
    payload = {
        "message_id": "e0a7b4f5",
        "status": "DELIVERED",
        "timestamp": "2025-08-25T14:30:00Z"
    }
    payload_bytes = json.dumps(payload).encode('utf-8')
    
    # Send the request
    response = client.post(
        url,
        payload_bytes,
        content_type="application/json"
    )
    
    assert response.status_code == 403 # Forbidden
