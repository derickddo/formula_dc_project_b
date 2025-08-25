# Project B: SMS Messaging Service

Project B is a  backend service designed to handle the sending of SMS messages, manage message status, and track delivery receipts (DLRs).

---

## Technology Stack

- **Django & Python**: Core web framework for API endpoints and business logic  
- **Celery**: Distributed task queue to handle background tasks (sending SMS, processing DLRs)  
- **Redis**: Message broker for Celery, enabling communication between web and worker services  
- **PostgreSQL**: Primary database for message storage and application data  
- **Docker & Docker Compose**: Orchestration for all services, providing a consistent isolated environment  

---

## 🚀 Getting Started

This project uses **Docker Compose** for a seamless setup. All services are defined in `docker-compose.yml`.

1. **Ensure Docker is Running**  
   Make sure the Docker daemon is active on your machine.

2. **Start the Services**  
   ```
    docker-compose up --build
   ```




## API Design

The API provides endpoints for sending messages, retrieving status, and receiving delivery reports.

### Create a new message

```
POST /api/messages/
Host: 127.0.0.1:8080
Content-Type: application/json
Idempotency-Key: send_msg:client_message_id_123

{
    "sender_id": "MyCorp",
    "recipient": "233241234567",
    "text": "Hello, this is a test message."
}
```


### Create a new message with invalid Sender ID
This request should fail because "BadSender" is not in the whitelist.
It should return a 400 Bad Request.
```
POST /api/messages/
Host: 127.0.0.1:8080
Content-Type: application/json
Idempotency-Key: send_msg:client_message_id_456

{
    "sender_id": "BadSender",
    "recipient": "233241234567",
    "text": "This message should be rejected."
}
```

### Create a new message (Contains "STOP" Keyword)
This request should fail because the message text contains the "STOP" keyword.
It should return a 400 Bad Request.
```
POST /api/messages/
Host: 127.0.0.1:8080
Content-Type: application/json
Idempotency-Key: send_msg:client_message_id_789

{
    "sender_id": "MyCorp",
    "recipient": "233241234567",
    "text": "Please STOP sending me messages."
}
```


### Get a message by ID
##### Replace <message_id> with a valid UUID
```
GET /api/messages/<message_id>/
Host: 127.0.0.1:8080
Accept: application/json
```

### Send a DLR webhook
##### Replace <provider_reference> with a valid reference from a sent message
##### Replace <hmac_sig> with a valid provider signature
```
POST /api/webhooks/dlr/
Host: 127.0.0.1:8080
Content-Type: application/json
X-Provider-Signature: <hmac_sig>

{
    "provider_reference": "<provider_reference>",
    "status": "DELIVERED"
}
```

How to Use:

- Install the REST Client extension in VS Code.

- Open the api.http file in the base directory.

- Hover over a request and click "Send Request".

- The first request sends a message.

- The second request automatically uses the id from the first response.