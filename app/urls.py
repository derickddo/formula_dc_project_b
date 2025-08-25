from django.urls import path
from .views import (
    MessageCreateView,
    MessageDetailView,
    DlrWebhookView,
)

urlpatterns = [
    # API endpoint to create a new message
    path('messages/', MessageCreateView.as_view(), name='message-create'),
    
    # API endpoint to retrieve a single message by ID
    path('messages/<uuid:pk>/', MessageDetailView.as_view(), name='message-detail'),
    
    # Webhook endpoint for receiving Delivery Receipts (DLRs)
    path('webhooks/dlr/', DlrWebhookView.as_view(), name='dlr-webhook'),
]
