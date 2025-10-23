# TripSage API Documentation

Internal API documentation for the TripSage travel planning platform. This API serves both the frontend application and AI agents with endpoints for authentication, trip management, flight/accommodation search, chat, and real-time communication.

## 🚀 Quick Start

### Development Environment

```bash
# Start the API server
uv run python -m tripsage.api.main

# API available at:
# - Main API: http://localhost:8000
# - Documentation: http://localhost:8000/docs
# - Alternative docs: http://localhost:8000/redoc
```

### First API Call

```bash
# Health check (no auth required)
curl http://localhost:8000/api/health

# Response:
# {"status": "healthy", "timestamp": "...", "version": "1.0.0"}
```

## 📚 API Documentation

### Core References

| Document | Description | Focus |
|----------|-------------|-------|
| **[REST API Reference](rest-endpoints.md)** | Complete endpoint documentation | All endpoints |
| **[Authentication Guide](authentication.md)** | JWT tokens, API keys, BYOK support | Auth & security |
| **[WebSocket API](websocket-api.md)** | Real-time communication | WebSocket endpoints |
| **[Usage Examples](usage-examples.md)** | Practical code snippets | Quick reference |
| **[Error Codes](error-codes.md)** | Error handling reference | Troubleshooting |

### Specialized Guides

- **[WebSocket Guide](websocket-guide.md)** - Connection management patterns
- **[Real-time Guide](realtime-guide.md)** - Real-time features and collaboration
- **[Dashboard API](dashboard-api.md)** - Monitoring and analytics endpoints
- **[Trip Security Examples](trip-security-usage-examples.md)** - Security-focused examples

## 🔐 Authentication

### JWT Authentication (Primary)

```bash
# Register user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secure_password"}'

# Login to get JWT
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "user@example.com", "password": "secure_password"}'

# Use JWT token
curl http://localhost:8000/api/v1/trips \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### API Key Authentication (BYOK)

```bash
# Create API key
curl -X POST http://localhost:8000/api/v1/keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"service": "duffel", "api_key": "user_key", "description": "Flight API"}'

# Use API key
curl http://localhost:8000/api/v1/flights/search \
  -H "X-API-Key: YOUR_API_KEY"
```

## 🌐 Core Endpoints

### Trip Management

- `GET /api/v1/trips` - List user trips
- `POST /api/v1/trips` - Create new trip
- `GET /api/v1/trips/{id}` - Get trip details
- `PUT /api/v1/trips/{id}` - Update trip
- `DELETE /api/v1/trips/{id}` - Delete trip

### Flight Operations

- `POST /api/v1/flights/search` - Search flights
- `GET /api/v1/flights/{id}` - Get flight details
- `POST /api/v1/flights/{id}/book` - Book flight
- `GET /api/v1/flights/bookings` - List user bookings

### Accommodation Operations

- `POST /api/v1/accommodations/search` - Search accommodations
- `GET /api/v1/accommodations/{id}` - Get details
- `POST /api/v1/accommodations/{id}/book` - Book accommodation

### AI & Chat

- `POST /api/v1/chat/completions` - AI chat interface
- `POST /api/v1/memory/conversation` - Store conversation
- `GET /api/v1/memory/context` - Get user context

### Real-time Communication

- `WS /api/v1/ws/trip/{trip_id}` - Trip collaboration
- `WS /api/v1/ws/chat/{session_id}` - Real-time chat
- `WS /api/v1/ws/status` - Agent progress updates

## 🛠️ Development Tools

### Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

### Testing

```bash
# Run API tests
uv run pytest tests/unit/tripsage/api/ --cov=tripsage.api

# Run integration tests
uv run pytest tests/integration/api/
```

## 📊 Response Formats

### Success Response

```json
{
  "data": {...},
  "meta": {
    "request_id": "req_123",
    "timestamp": "2025-06-17T10:30:00Z"
  }
}
```

### Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {...}
  },
  "meta": {
    "request_id": "req_456",
    "timestamp": "2025-06-17T10:30:00Z"
  }
}
```

## 🚨 Troubleshooting

| Issue | Solution | Reference |
|-------|----------|-----------|
| `401 Unauthorized` | Check JWT token format | [Auth Guide](authentication.md) |
| `422 Validation Error` | Verify required fields | [Error Codes](error-codes.md) |
| `429 Rate Limited` | Check rate limits | [Usage Examples](usage-examples.md) |
| WebSocket disconnect | Implement reconnection | [WebSocket Guide](websocket-guide.md) |

---

**Need help?** Check the [Usage Examples](usage-examples.md) for practical code samples or the [REST API Reference](rest-endpoints.md) for complete endpoint documentation.
