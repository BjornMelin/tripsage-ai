# API Usage Examples

> **Quick Reference for TripSage API Integration**  
> Practical code snippets for REST API, WebSocket, and authentication
> **Looking for complete tutorials?** Check out our [**Complete Integration Guide**](examples.md) for full workflows, SDKs, and advanced patterns.

## Table of Contents

- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [Flight Search](#flight-search)
- [Accommodation Search](#accommodation-search)
- [WebSocket Chat](#websocket-chat)
- [Trip Management](#trip-management)
- [🧠 AI Memory System](#-ai-memory-system)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [SDKs & Libraries](#sdks--libraries)

---

## Quick Start

### **Interactive Documentation**

TripSage provides automatic interactive API documentation:

- **Swagger UI**: `http://localhost:8001/api/docs`
- **ReDoc**: `http://localhost:8001/api/redoc`
- **OpenAPI Schema**: `http://localhost:8001/api/openapi.json`

### **Health Check**

Test your API connection:

```bash
curl http://localhost:8001/api/health
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2025-06-16T10:30:00Z",
  "version": "1.0.0",
  "environment": "development",
  "services": {
    "database": "healthy",
    "cache": "healthy",
    "external_apis": "healthy"
  }
}
```

---

## Authentication

### **JWT Authentication**

#### **Login to Get JWT Token**

```bash
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password"
  }'
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "user-123",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

#### **Using JWT Token**

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8001/api/profile
```

### **API Key Management**

#### **Generate API Key**

```bash
curl -X POST http://localhost:8001/api/user/keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Travel App",
    "permissions": ["flights:read", "accommodations:read", "trips:write"],
    "expires_at": "2025-12-31T23:59:59Z"
  }'
```

**Response:**

```json
{
  "id": "key-456",
  "name": "My Travel App",
  "key": "ts_live_1234567890abcdef...",
  "permissions": ["flights:read", "accommodations:read", "trips:write"],
  "created_at": "2025-06-16T10:30:00Z",
  "expires_at": "2025-12-31T23:59:59Z",
  "last_used": null
}
```

#### **List API Keys**

```bash
curl http://localhost:8001/api/user/keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### **Revoke API Key**

```bash
curl -X DELETE http://localhost:8001/api/user/keys/key-456 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Flight Search

### **Basic Flight Search**

```bash
curl -X POST http://localhost:8001/api/flights/search \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "NYC",
    "destination": "LAX",
    "departure_date": "2025-07-15",
    "return_date": "2025-07-22",
    "passengers": 1,
    "cabin_class": "economy"
  }'
```

**Response:**

```json
{
  "search_id": "search-789",
  "flights": [
    {
      "id": "flight-123",
      "airline": "American Airlines",
      "flight_number": "AA 123",
      "departure": {
        "airport": "JFK",
        "time": "2025-07-15T08:00:00Z",
        "terminal": "8"
      },
      "arrival": {
        "airport": "LAX",
        "time": "2025-07-15T11:30:00Z",
        "terminal": "4"
      },
      "duration": "5h 30m",
      "stops": 0,
      "price": {
        "amount": 299.99,
        "currency": "USD"
      },
      "booking_url": "https://api.tripsage.ai/flights/book/flight-123"
    }
  ],
  "total_results": 45,
  "search_time": "1.2s"
}
```

### **Flight Search with Filters with Filters**

```bash
curl -X POST http://localhost:8001/api/flights/search \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "NYC",
    "destination": "LAX",
    "departure_date": "2025-07-15",
    "return_date": "2025-07-22",
    "passengers": 2,
    "cabin_class": "business",
    "filters": {
      "max_price": 1500,
      "max_stops": 1,
      "preferred_airlines": ["AA", "DL", "UA"],
      "departure_time_range": {
        "earliest": "06:00",
        "latest": "10:00"
      }
    },
    "sort_by": "price",
    "limit": 20
  }'
```

### **Flight Price Alerts**

```bash
curl -X POST http://localhost:8001/api/flights/alerts \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "NYC",
    "destination": "LAX",
    "departure_date": "2025-07-15",
    "target_price": 250,
    "notification_method": "email"
  }'
```

---

## Accommodation Search

### **Hotel Search**

```bash
curl -X POST http://localhost:8001/api/accommodations/search \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Los Angeles, CA",
    "check_in": "2025-07-15",
    "check_out": "2025-07-22",
    "guests": 2,
    "rooms": 1,
    "budget_max": 200,
    "accommodation_type": "hotel"
  }'
```

**Response:**

```json
{
  "search_id": "search-456",
  "accommodations": [
    {
      "id": "hotel-789",
      "name": "The Beverly Hills Hotel",
      "type": "hotel",
      "rating": 4.8,
      "location": {
        "address": "9641 Sunset Blvd, Beverly Hills, CA",
        "coordinates": {
          "lat": 34.0901,
          "lng": -118.4065
        }
      },
      "amenities": ["wifi", "pool", "spa", "restaurant", "parking"],
      "price": {
        "per_night": 189.99,
        "total": 1329.93,
        "currency": "USD",
        "includes_taxes": true
      },
      "availability": "available",
      "booking_url": "https://api.tripsage.ai/accommodations/book/hotel-789"
    }
  ],
  "total_results": 127,
  "search_time": "0.8s"
}
```

### **Vacation Rental Search**

```bash
curl -X POST http://localhost:8001/api/accommodations/search \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Malibu, CA",
    "check_in": "2025-07-15",
    "check_out": "2025-07-22",
    "guests": 6,
    "accommodation_type": "vacation_rental",
    "filters": {
      "min_bedrooms": 3,
      "pet_friendly": true,
      "has_kitchen": true,
      "ocean_view": true
    }
  }'
```

---

## WebSocket Chat

### **JavaScript WebSocket Connection**

```javascript
// Connect to WebSocket
const ws = new WebSocket("ws://localhost:8001/api/chat/ws?token=YOUR_TOKEN");

ws.onopen = function (event) {
  console.log("Connected to TripSage Chat");

  // Send initial message
  ws.send(
    JSON.stringify({
      type: "user_message",
      content: "I want to plan a trip to Japan for 2 weeks",
      session_id: "session-123",
      metadata: {
        user_id: "user-456",
        preferences: {
          budget: 5000,
          interests: ["culture", "food", "technology"],
        },
      },
    })
  );
};

ws.onmessage = function (event) {
  const message = JSON.parse(event.data);
  console.log("Received:", message);

  switch (message.type) {
    case "ai_response":
      displayAIMessage(message.content);
      break;
    case "system_notification":
      showNotification(message.content);
      break;
    case "typing_indicator":
      showTypingIndicator(message.agent);
      break;
  }
};

ws.onerror = function (error) {
  console.error("WebSocket error:", error);
};

ws.onclose = function (event) {
  console.log("WebSocket connection closed:", event.code, event.reason);
};
```

### **Message Types**

#### **User Message**

```json
{
  "type": "user_message",
  "content": "Plan a 7-day trip to Paris with a budget of $3000",
  "session_id": "session-123",
  "timestamp": "2025-06-16T10:30:00Z",
  "metadata": {
    "user_id": "user-456",
    "message_id": "msg-789"
  }
}
```

#### **AI Response**

```json
{
  "type": "ai_response",
  "content": "I'd be happy to help plan your Paris trip! Based on your $3000 budget for 7 days, here's what I recommend...",
  "session_id": "session-123",
  "timestamp": "2025-06-16T10:30:15Z",
  "metadata": {
    "agent": "destination_research_agent",
    "confidence": 0.95,
    "sources": ["duffel", "booking.com", "google_maps"]
  }
}
```

#### **System Notification**

```json
{
  "type": "system_notification",
  "content": "Flight prices updated for your Paris trip - found 3 cheaper options!",
  "session_id": "session-123",
  "timestamp": "2025-06-16T10:31:00Z",
  "metadata": {
    "notification_type": "price_alert",
    "action_url": "/trips/trip-123/flights"
  }
}
```

### **Python WebSocket Client**

```python
import asyncio
import websockets
import json

async def chat_client():
    uri = "ws://localhost:8001/api/chat/ws?token=YOUR_TOKEN"

    async with websockets.connect(uri) as websocket:
        # Send message
        message = {
            "type": "user_message",
            "content": "Find me flights from NYC to Tokyo",
            "session_id": "session-456"
        }
        await websocket.send(json.dumps(message))

        # Listen for responses
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")

            if data['type'] == 'ai_response':
                print(f"AI: {data['content']}")

# Run the client
asyncio.run(chat_client())
```

---

## Trip Management

### **Create Trip**

```bash
curl -X POST http://localhost:8001/api/trips \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "European Adventure",
    "description": "Two-week tour of Europe",
    "start_date": "2025-08-01",
    "end_date": "2025-08-14",
    "budget": 5000,
    "destinations": ["Paris", "Rome", "Barcelona"],
    "travelers": 2,
    "preferences": {
      "accommodation_type": "hotel",
      "budget_tier": "mid-range",
      "interests": ["culture", "food", "history"],
      "pace": "moderate"
    }
  }'
```

**Response:**

```json
{
  "id": "trip-123",
  "name": "European Adventure",
  "status": "planning",
  "created_at": "2025-06-16T10:30:00Z",
  "itinerary": {
    "days": 14,
    "destinations": 3,
    "estimated_cost": 4750
  },
  "share_url": "https://tripsage.ai/trips/trip-123/share"
}
```

### **Get Trip Details**

```bash
curl http://localhost:8001/api/trips/trip-123 \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### **Update Trip**

```bash
curl -X PATCH http://localhost:8001/api/trips/trip-123 \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "budget": 6000,
    "preferences": {
      "budget_tier": "luxury"
    }
  }'
```

### **Add Collaborators**

```bash
curl -X POST http://localhost:8001/api/trips/trip-123/collaborators \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "friend@example.com",
    "role": "editor",
    "message": "Join me in planning our European adventure!"
  }'
```

---

## 🧠 AI Memory System

### **Add Memory**

```bash
curl -X POST http://localhost:8001/api/memory \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User prefers window seats on flights and hotels with ocean views",
    "category": "preferences",
    "metadata": {
      "confidence": 0.9,
      "source": "user_conversation"
    }
  }'
```

### **Search Memory**

```bash
curl -X POST http://localhost:8001/api/memory/search \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "flight preferences",
    "limit": 10,
    "threshold": 0.7
  }'
```

**Response:**

```json
{
  "memories": [
    {
      "id": "memory-123",
      "content": "User prefers window seats on flights and hotels with ocean views",
      "category": "preferences",
      "relevance_score": 0.95,
      "created_at": "2025-06-16T10:30:00Z"
    }
  ],
  "total_results": 1
}
```

### **Get User Memory Summary**

```bash
curl http://localhost:8001/api/memory/summary \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Rate Limiting

### **Check Rate Limit Status**

Rate limit information is included in response headers:

```bash
curl -I http://localhost:8001/api/health \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Headers:**

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642284000
X-RateLimit-Window: 3600
```

### **Handle Rate Limiting**

```javascript
async function makeAPICall(url, options) {
  const response = await fetch(url, options);

  // Check rate limit headers
  const remaining = response.headers.get("X-RateLimit-Remaining");
  const reset = response.headers.get("X-RateLimit-Reset");

  if (response.status === 429) {
    const retryAfter = response.headers.get("Retry-After");
    console.log(`Rate limited. Retry after ${retryAfter} seconds`);

    // Wait and retry
    await new Promise((resolve) => setTimeout(resolve, retryAfter * 1000));
    return makeAPICall(url, options);
  }

  return response.json();
}
```

---

## Error Handling

### **Standard Error Response**

```json
{
  "error": true,
  "message": "Invalid destination code",
  "code": "INVALID_DESTINATION",
  "details": {
    "field": "destination",
    "value": "INVALID",
    "allowed_values": ["NYC", "LAX", "LHR", "..."]
  },
  "request_id": "req-123456",
  "timestamp": "2025-06-16T10:30:00Z"
}
```

### **Common Error Codes**

| Code                   | Status | Description                  |
| ---------------------- | ------ | ---------------------------- |
| `AUTHENTICATION_ERROR` | 401    | Invalid or expired token     |
| `AUTHORIZATION_ERROR`  | 403    | Insufficient permissions     |
| `VALIDATION_ERROR`     | 400    | Invalid request data         |
| `NOT_FOUND`            | 404    | Resource not found           |
| `RATE_LIMITED`         | 429    | Too many requests            |
| `EXTERNAL_API_ERROR`   | 502    | External service unavailable |
| `INTERNAL_ERROR`       | 500    | Server error                 |

### **Error Handling Best Practices**

```javascript
async function handleAPIResponse(response) {
  if (!response.ok) {
    const error = await response.json();

    switch (error.code) {
      case "AUTHENTICATION_ERROR":
        // Refresh token or redirect to login
        await refreshToken();
        break;

      case "RATE_LIMITED":
        // Implement exponential backoff
        const retryAfter = response.headers.get("Retry-After");
        await delay(retryAfter * 1000);
        break;

      case "VALIDATION_ERROR":
        // Show user-friendly validation errors
        showValidationErrors(error.details);
        break;

      default:
        // Log error and show generic message
        console.error("API Error:", error);
        showErrorMessage("Something went wrong. Please try again.");
    }

    throw new Error(error.message);
  }

  return response.json();
}
```

---

## SDKs & Libraries

### **Python SDK (Coming Soon)**

```python
from tripsage import TripSage

# Initialize client
client = TripSage(api_key="your_api_key")

# Search flights
flights = await client.flights.search(
    origin="NYC",
    destination="LAX",
    departure_date="2025-07-15",
    passengers=1
)

# Create trip
trip = await client.trips.create(
    name="California Adventure",
    destinations=["Los Angeles", "San Francisco"],
    budget=3000
)

# Start chat session
async with client.chat.session() as chat:
    response = await chat.send("Plan a trip to Japan")
    print(response.content)
```

### **JavaScript/TypeScript SDK (Coming Soon)**

```typescript
import { TripSage } from "@tripsage/sdk";

// Initialize client
const client = new TripSage({
  apiKey: "your_api_key",
  baseURL: "https://api.tripsage.ai",
});

// Search accommodations
const hotels = await client.accommodations.search({
  location: "Paris, France",
  checkIn: "2025-07-15",
  checkOut: "2025-07-22",
  guests: 2,
});

// WebSocket chat
const chat = client.chat.connect();
chat.on("message", (message) => {
  console.log("AI:", message.content);
});

await chat.send("Find me flights to Tokyo");
```

### **React Hooks (Coming Soon)**

```jsx
import { useTripSage, useFlightSearch, useChat } from "@tripsage/react";

function FlightSearchComponent() {
  const {
    data: flights,
    loading,
    error,
  } = useFlightSearch({
    origin: "NYC",
    destination: "LAX",
    departureDate: "2025-07-15",
  });

  const { messages, sendMessage, isConnected } = useChat();

  if (loading) return <div>Searching flights...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <h2>Available Flights</h2>
      {flights.map((flight) => (
        <FlightCard key={flight.id} flight={flight} />
      ))}
    </div>
  );
}
```

---

## � Trip Security

This section demonstrates how to use the trip access verification system in TripSage API endpoints.

### **Overview**

The trip security system provides access control for trip-related operations through:

- **Access Levels**: `READ`, `WRITE`, `OWNER`, `COLLABORATOR`
- **Permissions**: `VIEW`, `EDIT`, `MANAGE`
- **FastAPI Dependencies**: Pre-configured and custom dependency injection
- **Decorators**: Clean, declarative endpoint protection
- **Audit Logging**: Security event tracking

### **Using Pre-configured Dependencies**

```python
from fastapi import APIRouter, status
from tripsage.api.core.trip_security import (
    TripReadAccessDep,
    TripOwnerAccessDep,
    TripEditPermissionDep,
)
from tripsage.api.core.dependencies import RequiredPrincipalDep

router = APIRouter(tags=["trips"])

@router.get("/trips/{trip_id}")
async def get_trip(
    trip_id: str,
    access_result: TripReadAccessDep,  # Verifies read access
    principal: RequiredPrincipalDep,
):
    """Get trip details - requires read access."""
    # Access already verified, proceed with operation
    return {"trip_id": trip_id, "access_level": access_result.access_level}

@router.delete("/trips/{trip_id}")
async def delete_trip(
    trip_id: str,
    access_result: TripOwnerAccessDep,  # Verifies owner access
    principal: RequiredPrincipalDep,
):
    """Delete trip - requires owner access."""
    # Only trip owner can delete
    return {"message": "Trip deleted successfully"}

@router.put("/trips/{trip_id}")
async def update_trip(
    trip_id: str,
    access_result: TripEditPermissionDep,  # Verifies edit permission
    principal: RequiredPrincipalDep,
):
    """Update trip - requires edit permission."""
    # Owner or collaborators with edit permission can update
    return {"message": "Trip updated successfully"}
```

### **Using Decorators**

```python
from tripsage.api.core.trip_security import (
    require_trip_access,
    TripAccessLevel,
    TripAccessPermission,
)

@router.get("/trips/{trip_id}/details")
@require_trip_access(TripAccessLevel.READ)
async def get_trip_details(
    trip_id: str,
    principal: RequiredPrincipalDep,
):
    """Get detailed trip information."""
    # Access verification handled by decorator
    return {"trip_id": trip_id, "details": "..."}

@router.post("/trips/{trip_id}/collaborators")
@require_trip_access(
    TripAccessLevel.COLLABORATOR,
    TripAccessPermission.MANAGE
)
async def add_collaborator(
    trip_id: str,
    principal: RequiredPrincipalDep,
):
    """Add collaborator - requires manage permission."""
    # Only users with manage permission can add collaborators
    return {"message": "Collaborator added"}
```

### **Custom Dependencies**

```python
from tripsage.api.core.trip_security import (
    create_trip_access_dependency,
    TripAccessLevel,
    TripAccessPermission,
)
from typing import Annotated
from fastapi import Depends

# Create custom dependency for specific use case
ViewOnlyAccessDep = Annotated[
    TripAccessResult,
    Depends(create_trip_access_dependency(
        TripAccessLevel.COLLABORATOR,
        TripAccessPermission.VIEW
    ))
]

@router.get("/trips/{trip_id}/readonly-summary")
async def get_readonly_summary(
    trip_id: str,
    access_result: ViewOnlyAccessDep,
    principal: RequiredPrincipalDep,
):
    """Get read-only trip summary."""
    return {
        "trip_id": trip_id,
        "can_edit": access_result.permission_granted in [
            TripAccessPermission.EDIT,
            TripAccessPermission.MANAGE
        ]
    }
```

### **Multiple Access Checks**

```python
from tripsage.api.core.trip_security import (
    check_trip_ownership,
    check_trip_collaboration,
    get_user_trip_permissions,
)

@router.get("/trips/{trip_id}/permissions")
async def get_trip_permissions(
    trip_id: str,
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """Get detailed permission information for current user."""
    permissions = await get_user_trip_permissions(
        trip_id, principal, trip_service
    )
    return permissions

@router.post("/trips/{trip_id}/conditional-action")
async def conditional_action(
    trip_id: str,
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """Perform different actions based on access level."""
    is_owner = await check_trip_ownership(trip_id, principal, trip_service)

    if is_owner:
        # Owner-specific logic
        return {"action": "owner_action_performed"}

    has_collab = await check_trip_collaboration(
        trip_id, principal, trip_service, TripAccessPermission.EDIT
    )

    if has_collab:
        # Collaborator logic
        return {"action": "collaborator_action_performed"}

    # Read-only logic
    return {"action": "readonly_action_performed"}
```

### **Error Handling**

```python
from tripsage_core.exceptions.exceptions import (
    CoreAuthorizationError,
    CoreResourceNotFoundError,
)

@router.put("/trips/{trip_id}/sensitive-data")
async def update_sensitive_data(
    trip_id: str,
    access_result: TripOwnerAccessDep,
    principal: RequiredPrincipalDep,
):
    """Update sensitive trip data - owner only."""
    try:
        # The dependency already verified owner access
        # Proceed with sensitive operation
        return {"message": "Sensitive data updated"}
    except Exception as e:
        # Handle any additional errors
        logger.exception(f"Failed to update sensitive data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update trip data"
        )
```

### **WebSocket Security**

```python
from fastapi import WebSocket, WebSocketDisconnect
from tripsage.api.core.trip_security import verify_trip_access, TripAccessContext

@router.websocket("/trips/{trip_id}/live-updates")
async def trip_live_updates(
    websocket: WebSocket,
    trip_id: str,
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """WebSocket endpoint with trip access verification."""
    # Verify access before accepting connection
    context = TripAccessContext(
        trip_id=trip_id,
        principal_id=principal.id,
        required_level=TripAccessLevel.READ,
        operation="websocket_connection",
        ip_address=websocket.client.host if websocket.client else "unknown",
    )

    access_result = await verify_trip_access(context, trip_service)
    if not access_result.is_authorized:
        await websocket.close(code=1008, reason="Access denied")
        return

    await websocket.accept()
    try:
        while True:
            # Handle WebSocket communication
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        pass
```

### **Updating Existing Trip Endpoints**

```python
# Before - Manual access checking
@router.get("/trips/{trip_id}")
async def get_trip_old(
    trip_id: str,
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    # Manual access check (old way)
    has_access = await trip_service._check_trip_access(trip_id, principal.id)
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")

    # Rest of logic...

# After - Using new security system
@router.get("/trips/{trip_id}")
async def get_trip_new(
    trip_id: str,
    access_result: TripReadAccessDep,  # Automatic verification
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    # Access already verified, proceed directly
    # Additional context available in access_result
    logger.info(f"User {principal.id} accessing trip {trip_id} as {access_result.access_level}")
    # Rest of logic...
```

### **Collaboration Endpoints**

```python
@router.get("/trips/{trip_id}/collaborators")
@require_trip_access(TripAccessLevel.COLLABORATOR)
async def list_collaborators(
    trip_id: str,
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """List trip collaborators - any collaborator can view."""
    # Implementation here
    pass

@router.post("/trips/{trip_id}/collaborators")
async def add_collaborator(
    trip_id: str,
    access_result: TripManagePermissionDep,  # Requires manage permission
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """Add collaborator - requires manage permission."""
    if not access_result.permission_granted == TripAccessPermission.MANAGE:
        raise HTTPException(
            status_code=403,
            detail="Adding collaborators requires manage permission"
        )
    # Implementation here
    pass

@router.delete("/trips/{trip_id}/collaborators/{user_id}")
async def remove_collaborator(
    trip_id: str,
    user_id: str,
    access_result: TripOwnerAccessDep,  # Only owner can remove
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """Remove collaborator - owner only."""
    # Implementation here
    pass
```

### **Best Practices**

#### **1. Choose Appropriate Access Levels**

```python
# For viewing operations
access_result: TripReadAccessDep

# For editing trip content
access_result: TripEditPermissionDep

# For managing collaborators, settings
access_result: TripManagePermissionDep

# For deleting trips, changing ownership
access_result: TripOwnerAccessDep
```

#### **2. Use Meaningful Operation Names**

```python
context = TripAccessContext(
    trip_id=trip_id,
    principal_id=principal.id,
    required_level=TripAccessLevel.WRITE,
    operation="update_trip_itinerary",  # Descriptive operation name
)
```

#### **3. Handle Access Results Appropriately**

```python
@router.post("/trips/{trip_id}/action")
async def trip_action(
    trip_id: str,
    access_result: TripCollaboratorAccessDep,
    principal: RequiredPrincipalDep,
):
    # Use access result information to customize response
    response = {"trip_id": trip_id}

    if access_result.is_owner:
        response["owner_actions"] = ["delete", "transfer_ownership"]

    if access_result.permission_granted == TripAccessPermission.MANAGE:
        response["manage_actions"] = ["add_collaborator", "change_settings"]

    if access_result.permission_granted in [TripAccessPermission.EDIT, TripAccessPermission.MANAGE]:
        response["edit_actions"] = ["update_itinerary", "add_notes"]

    return response
```

#### **4. Audit Important Operations**

```python
# The system automatically audits access events, but you can add
# operation-specific auditing for important actions

from tripsage_core.services.business.audit_logging_service import audit_security_event

@router.delete("/trips/{trip_id}")
async def delete_trip(
    trip_id: str,
    access_result: TripOwnerAccessDep,
    principal: RequiredPrincipalDep,
):
    # Perform deletion
    # ...

    # Additional audit for trip deletion
    await audit_security_event(
        event_type=AuditEventType.DATA_DELETION,
        severity=AuditSeverity.HIGH,
        message=f"Trip {trip_id} deleted by owner",
        actor_id=principal.id,
        target_resource=trip_id,
        risk_score=80,
    )

    return {"message": "Trip deleted successfully"}
```

### **Testing**

#### **Unit Tests**

```python
import pytest
from tripsage.api.core.trip_security import verify_trip_access, TripAccessContext

@pytest.mark.asyncio
async def test_trip_access_verification():
    # Mock dependencies and test access verification
    context = TripAccessContext(
        trip_id="test-trip-id",
        principal_id="test-user-id",
        required_level=TripAccessLevel.READ,
        operation="test_operation",
    )

    # Test with mocked trip service
    result = await verify_trip_access(context, mock_trip_service)
    assert result.is_authorized
```

#### **Integration Tests**

```python
from fastapi.testclient import TestClient

def test_trip_endpoint_security(client: TestClient):
    # Test that endpoint requires authentication
    response = client.get("/api/trips/test-id")
    assert response.status_code == 401

    # Test with valid authentication
    headers = {"Authorization": "Bearer valid-token"}
    response = client.get("/api/trips/test-id", headers=headers)
    # Should succeed or return 403 based on access rights
    assert response.status_code in [200, 403]
```

---

## Additional Resources

### **API Documentation**

- **[Complete API Reference](rest-endpoints.md)** - Full endpoint documentation
- **[Interactive Docs](http://localhost:8001/api/docs)** - Test endpoints in browser
- **[OpenAPI Schema](http://localhost:8001/api/openapi.json)** - Machine-readable API spec

### **Development Resources**

- **[Developer Guide](../04_DEVELOPMENT_GUIDE/README.md)** - Setup and development
- **[Configuration](../07_CONFIGURATION/README.md)** - Environment setup
- **[Getting Started](../01_GETTING_STARTED/README.md)** - Quick start guide

### **Support**

- **[FAQ](FAQ.md)** - Common questions and answers
- **[Discord](https://discord.gg/tripsage)** - Developer community
- **[Email](mailto:developers@tripsage.ai)** - Direct developer support

---

**Ready to build amazing travel experiences?** Start with our [interactive API documentation](http://localhost:8001/api/docs) and join our [developer community](https://discord.gg/tripsage)!

> _Last updated: June 16, 2025_
