# 🔌 API Usage Examples

> **Quick Reference for TripSage API Integration**  
> Practical code snippets for REST API, WebSocket, and authentication
> **💡 Looking for complete tutorials?** Check out our [**Complete Integration Guide**](examples.md) for full workflows, SDKs, and advanced patterns.

## 📋 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [🔑 Authentication](#-authentication)
- [✈️ Flight Search](#️-flight-search)
- [🏨 Accommodation Search](#-accommodation-search)
- [💬 WebSocket Chat](#-websocket-chat)
- [🗺️ Trip Management](#️-trip-management)
- [🧠 AI Memory System](#-ai-memory-system)
- [📊 Rate Limiting](#-rate-limiting)
- [🐛 Error Handling](#-error-handling)
- [🔧 SDKs & Libraries](#-sdks--libraries)

---

## 🚀 Quick Start

### **Interactive Documentation**

TripSage provides automatic interactive API documentation:

- **📚 Swagger UI**: `http://localhost:8001/api/docs`
- **📖 ReDoc**: `http://localhost:8001/api/redoc`
- **🔧 OpenAPI Schema**: `http://localhost:8001/api/openapi.json`

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

## 🔑 Authentication

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

## ✈️ Flight Search

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

### **Advanced Flight Search with Filters**

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

## 🏨 Accommodation Search

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

## 💬 WebSocket Chat

### **JavaScript WebSocket Connection**

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8001/api/chat/ws?token=YOUR_TOKEN');

ws.onopen = function(event) {
    console.log('Connected to TripSage Chat');
    
    // Send initial message
    ws.send(JSON.stringify({
        type: 'user_message',
        content: 'I want to plan a trip to Japan for 2 weeks',
        session_id: 'session-123',
        metadata: {
            user_id: 'user-456',
            preferences: {
                budget: 5000,
                interests: ['culture', 'food', 'technology']
            }
        }
    }));
};

ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log('Received:', message);
    
    switch(message.type) {
        case 'ai_response':
            displayAIMessage(message.content);
            break;
        case 'system_notification':
            showNotification(message.content);
            break;
        case 'typing_indicator':
            showTypingIndicator(message.agent);
            break;
    }
};

ws.onerror = function(error) {
    console.error('WebSocket error:', error);
};

ws.onclose = function(event) {
    console.log('WebSocket connection closed:', event.code, event.reason);
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

## 🗺️ Trip Management

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

## 📊 Rate Limiting

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
    const remaining = response.headers.get('X-RateLimit-Remaining');
    const reset = response.headers.get('X-RateLimit-Reset');
    
    if (response.status === 429) {
        const retryAfter = response.headers.get('Retry-After');
        console.log(`Rate limited. Retry after ${retryAfter} seconds`);
        
        // Wait and retry
        await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
        return makeAPICall(url, options);
    }
    
    return response.json();
}
```

---

## 🐛 Error Handling

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

| Code | Status | Description |
|------|--------|-------------|
| `AUTHENTICATION_ERROR` | 401 | Invalid or expired token |
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Too many requests |
| `EXTERNAL_API_ERROR` | 502 | External service unavailable |
| `INTERNAL_ERROR` | 500 | Server error |

### **Error Handling Best Practices**

```javascript
async function handleAPIResponse(response) {
    if (!response.ok) {
        const error = await response.json();
        
        switch (error.code) {
            case 'AUTHENTICATION_ERROR':
                // Refresh token or redirect to login
                await refreshToken();
                break;
                
            case 'RATE_LIMITED':
                // Implement exponential backoff
                const retryAfter = response.headers.get('Retry-After');
                await delay(retryAfter * 1000);
                break;
                
            case 'VALIDATION_ERROR':
                // Show user-friendly validation errors
                showValidationErrors(error.details);
                break;
                
            default:
                // Log error and show generic message
                console.error('API Error:', error);
                showErrorMessage('Something went wrong. Please try again.');
        }
        
        throw new Error(error.message);
    }
    
    return response.json();
}
```

---

## 🔧 SDKs & Libraries

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
import { TripSage } from '@tripsage/sdk';

// Initialize client
const client = new TripSage({
  apiKey: 'your_api_key',
  baseURL: 'https://api.tripsage.ai'
});

// Search accommodations
const hotels = await client.accommodations.search({
  location: 'Paris, France',
  checkIn: '2025-07-15',
  checkOut: '2025-07-22',
  guests: 2
});

// WebSocket chat
const chat = client.chat.connect();
chat.on('message', (message) => {
  console.log('AI:', message.content);
});

await chat.send('Find me flights to Tokyo');
```

### **React Hooks (Coming Soon)**

```jsx
import { useTripSage, useFlightSearch, useChat } from '@tripsage/react';

function FlightSearchComponent() {
  const { data: flights, loading, error } = useFlightSearch({
    origin: 'NYC',
    destination: 'LAX',
    departureDate: '2025-07-15'
  });

  const { messages, sendMessage, isConnected } = useChat();

  if (loading) return <div>Searching flights...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <h2>Available Flights</h2>
      {flights.map(flight => (
        <FlightCard key={flight.id} flight={flight} />
      ))}
    </div>
  );
}
```

---

## 🔗 Additional Resources

### **API Documentation**

- **[📚 Complete API Reference](rest-endpoints.md)** - Full endpoint documentation
- **[🔧 Interactive Docs](http://localhost:8001/api/docs)** - Test endpoints in browser
- **[📖 OpenAPI Schema](http://localhost:8001/api/openapi.json)** - Machine-readable API spec

### **Development Resources**

- **[👨‍💻 Developer Guide](../04_DEVELOPMENT_GUIDE/README.md)** - Setup and development
- **[🔧 Configuration](../07_CONFIGURATION/README.md)** - Environment setup
- **[🚀 Getting Started](../01_GETTING_STARTED/README.md)** - Quick start guide

### **Support**

- **[❓ FAQ](FAQ.md)** - Common questions and answers
- **[💬 Discord](https://discord.gg/tripsage)** - Developer community
- **[📧 Email](mailto:developers@tripsage.ai)** - Direct developer support

---

**Ready to build amazing travel experiences?** Start with our [interactive API documentation](http://localhost:8001/api/docs) and join our [developer community](https://discord.gg/tripsage)! 🚀

> *Last updated: June 16, 2025*
