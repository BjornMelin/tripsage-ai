# 🔌 TripSage REST API Endpoints

> **Complete API Reference**  
> Comprehensive documentation for all TripSage REST API endpoints including trip collaboration, real-time features, and data management.

## 📋 API Overview

- **Base URL**: `https://api.tripsage.ai/v1`
- **Authentication**: Bearer JWT token, API key
- **Content-Type**: `application/json`
- **Rate Limiting**: 1000 requests/hour (standard tier)

## 🔐 Authentication

All API endpoints require authentication via JWT token:

```http
GET /api/v1/trips
Authorization: Bearer your-jwt-token
Content-Type: application/json
```

## 🗺️ Trip Management

### Create Trip

```http
POST /api/v1/trips
```

**Request Body:**
```json
{
  "title": "Summer Vacation in Europe",
  "description": "A two-week tour of Western Europe",
  "start_date": "2025-06-01",
  "end_date": "2025-06-15",
  "destinations": [
    {
      "name": "Paris",
      "country": "France",
      "city": "Paris",
      "coordinates": {
        "latitude": 48.8566,
        "longitude": 2.3522
      }
    }
  ],
  "preferences": {
    "budget": {
      "total": 5000,
      "currency": "USD"
    },
    "accommodation": {
      "type": "hotel",
      "min_rating": 4.0
    }
  }
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "user123",
  "title": "Summer Vacation in Europe",
  "description": "A two-week tour of Western Europe",
  "start_date": "2025-06-01",
  "end_date": "2025-06-15",
  "duration_days": 14,
  "destinations": [...],
  "preferences": {...},
  "status": "planning",
  "created_at": "2025-01-15T14:30:00Z",
  "updated_at": "2025-01-16T09:45:00Z"
}
```

### Get Trip

```http
GET /api/v1/trips/{trip_id}
```

**Response:** Same as create trip response

### Update Trip

```http
PUT /api/v1/trips/{trip_id}
```

**Request Body:** (All fields optional)
```json
{
  "title": "Updated Trip Title",
  "description": "Updated description",
  "start_date": "2025-06-02",
  "end_date": "2025-06-16"
}
```

### Delete Trip

```http
DELETE /api/v1/trips/{trip_id}
```

**Response:** `204 No Content`

### List User Trips

```http
GET /api/v1/trips?skip=0&limit=10
```

**Response:**
```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "title": "Summer Vacation in Europe",
      "start_date": "2025-06-01",
      "end_date": "2025-06-15",
      "duration_days": 14,
      "destinations": ["Paris", "Rome", "Barcelona"],
      "status": "planning",
      "created_at": "2025-01-15T14:30:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 10
}
```

### Search Trips

```http
GET /api/v1/trips/search?q=europe&status=planning&skip=0&limit=10
```

### Duplicate Trip

```http
POST /api/v1/trips/{trip_id}/duplicate
```

### Trip Summary

```http
GET /api/v1/trips/{trip_id}/summary
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Summer Vacation in Europe",
  "date_range": "Jun 1-15, 2025",
  "duration_days": 14,
  "destinations": ["Paris", "Rome", "Barcelona"],
  "accommodation_summary": "4-star hotels in city centers",
  "transportation_summary": "Economy flights with 1 connection",
  "budget_summary": {
    "total": 5000,
    "currency": "USD",
    "spent": 1500,
    "remaining": 3500,
    "breakdown": {
      "accommodation": {"budget": 2000, "spent": 800},
      "transportation": {"budget": 1500, "spent": 700}
    }
  },
  "has_itinerary": true,
  "completion_percentage": 75
}
```

### Trip Preferences

```http
PUT /api/v1/trips/{trip_id}/preferences
```

**Request Body:**
```json
{
  "budget": {
    "total": 6000,
    "currency": "USD",
    "accommodation_budget": 2500,
    "transportation_budget": 2000
  },
  "accommodation": {
    "type": "hotel",
    "min_rating": 4.5,
    "amenities": ["wifi", "breakfast", "pool"]
  }
}
```

### Trip Itinerary

```http
GET /api/v1/trips/{trip_id}/itinerary
```

### Export Trip

```http
POST /api/v1/trips/{trip_id}/export?format=pdf
```

### Trip Suggestions

```http
GET /api/v1/trips/suggestions?limit=4&budget_max=3000&category=culture
```

**Response:**
```json
[
  {
    "id": "suggestion-1",
    "title": "Tokyo Cherry Blossom Adventure",
    "destination": "Tokyo, Japan",
    "description": "Experience the magic of cherry blossom season...",
    "estimated_price": 2800,
    "currency": "USD",
    "duration": 7,
    "rating": 4.8,
    "category": "culture",
    "best_time_to_visit": "March - May",
    "highlights": ["Cherry Blossoms", "Temples", "Street Food"],
    "trending": true,
    "seasonal": true
  }
]
```

## 🤝 Trip Collaboration

### Share Trip

```http
POST /api/v1/trips/{trip_id}/share
```

**Request Body:**
```json
{
  "user_emails": ["friend@example.com", "family@example.com"],
  "permission_level": "edit",
  "message": "Let's plan our vacation together!"
}
```

**Response:**
```json
[
  {
    "user_id": "456e7890-e89b-12d3-a456-426614174001",
    "email": "friend@example.com",
    "name": "John Doe",
    "permission_level": "edit",
    "added_by": "123e4567-e89b-12d3-a456-426614174000",
    "added_at": "2025-01-16T10:00:00Z",
    "is_active": true
  }
]
```

### List Trip Collaborators

```http
GET /api/v1/trips/{trip_id}/collaborators
```

**Response:**
```json
{
  "collaborators": [
    {
      "user_id": "456e7890-e89b-12d3-a456-426614174001",
      "email": "friend@example.com",
      "name": "John Doe",
      "permission_level": "edit",
      "added_by": "123e4567-e89b-12d3-a456-426614174000",
      "added_at": "2025-01-16T10:00:00Z",
      "is_active": true
    }
  ],
  "total": 1,
  "owner_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

### Update Collaborator Permissions

```http
PUT /api/v1/trips/{trip_id}/collaborators/{user_id}
```

**Request Body:**
```json
{
  "permission_level": "admin"
}
```

### Remove Collaborator

```http
DELETE /api/v1/trips/{trip_id}/collaborators/{user_id}
```

**Response:** `204 No Content`

## 🔍 Search & Discovery

### Search Destinations

```http
GET /api/v1/destinations/search?q=paris&limit=10
```

**Response:**
```json
{
  "results": [
    {
      "id": "dest_001",
      "name": "Paris",
      "country": "France",
      "description": "The City of Light",
      "coordinates": {
        "latitude": 48.8566,
        "longitude": 2.3522
      },
      "rating": 4.7,
      "highlights": ["Eiffel Tower", "Louvre Museum", "Notre-Dame"]
    }
  ],
  "total": 1
}
```

### Search Flights

```http
GET /api/v1/flights/search
```

**Query Parameters:**
- `origin`: Origin airport code (required)
- `destination`: Destination airport code (required)
- `departure_date`: Departure date (required)
- `return_date`: Return date (optional)
- `passengers`: Number of passengers (default: 1)
- `class`: Seat class (economy, business, first)

**Response:**
```json
{
  "results": [
    {
      "id": "flight_001",
      "airline": "Air France",
      "flight_number": "AF123",
      "origin": {
        "code": "JFK",
        "name": "John F. Kennedy International",
        "city": "New York"
      },
      "destination": {
        "code": "CDG",
        "name": "Charles de Gaulle",
        "city": "Paris"
      },
      "departure_time": "2025-06-01T14:30:00Z",
      "arrival_time": "2025-06-02T02:45:00Z",
      "duration": "7h 15m",
      "price": {
        "amount": 850.00,
        "currency": "USD"
      },
      "stops": 0,
      "booking_class": "economy"
    }
  ],
  "total": 25,
  "filters_applied": {
    "max_price": 1000,
    "max_stops": 1
  }
}
```

### Search Accommodations

```http
GET /api/v1/accommodations/search
```

**Query Parameters:**
- `destination`: Destination name or coordinates
- `check_in`: Check-in date
- `check_out`: Check-out date
- `guests`: Number of guests
- `type`: Accommodation type (hotel, apartment, etc.)
- `min_rating`: Minimum rating (1-5)

**Response:**
```json
{
  "results": [
    {
      "id": "hotel_001",
      "name": "Hotel de Luxe Paris",
      "type": "hotel",
      "rating": 4.5,
      "address": "123 Rue de Rivoli, Paris",
      "coordinates": {
        "latitude": 48.8566,
        "longitude": 2.3522
      },
      "price_per_night": {
        "amount": 250.00,
        "currency": "USD"
      },
      "total_price": {
        "amount": 1750.00,
        "currency": "USD"
      },
      "amenities": ["wifi", "breakfast", "pool", "gym"],
      "images": ["url1", "url2"],
      "availability": true
    }
  ]
}
```

### Search Activities

```http
GET /api/v1/activities/search?destination=paris&category=museums&date=2025-06-01
```

## 💬 Chat & AI

### Start Chat Session

```http
POST /api/v1/chat/sessions
```

**Response:**
```json
{
  "session_id": "session_123",
  "created_at": "2025-01-16T10:00:00Z"
}
```

### Send Chat Message

```http
POST /api/v1/chat/sessions/{session_id}/messages
```

**Request Body:**
```json
{
  "content": "Help me find flights from New York to Paris",
  "attachments": []
}
```

**Response:**
```json
{
  "id": "msg_001",
  "role": "user",
  "content": "Help me find flights from New York to Paris",
  "timestamp": "2025-01-16T10:00:00Z",
  "session_id": "session_123"
}
```

### Get Chat History

```http
GET /api/v1/chat/sessions/{session_id}/messages?limit=50
```

## 🧠 Memory & Preferences

### Get User Memory

```http
GET /api/v1/memory/conversations?session_id={session_id}
```

### Update User Preferences

```http
PUT /api/v1/memory/preferences
```

**Request Body:**
```json
{
  "travel_style": "luxury",
  "preferred_airlines": ["Air France", "British Airways"],
  "dietary_restrictions": ["vegetarian"],
  "accessibility_needs": []
}
```

## 🔑 API Key Management

### List API Keys

```http
GET /api/v1/keys
```

**Response:**
```json
{
  "keys": [
    {
      "id": "key_001",
      "name": "Production App",
      "service_type": "external",
      "provider": "duffel",
      "masked_key": "duf_***************xyz",
      "created_at": "2025-01-15T14:30:00Z",
      "last_used": "2025-01-16T09:45:00Z",
      "is_active": true
    }
  ]
}
```

### Create API Key

```http
POST /api/v1/keys
```

**Request Body:**
```json
{
  "name": "My Integration",
  "service_type": "external",
  "provider": "duffel",
  "api_key": "duf_test_abc123xyz"
}
```

### Update API Key

```http
PUT /api/v1/keys/{key_id}
```

### Delete API Key

```http
DELETE /api/v1/keys/{key_id}
```

## 🎯 Attachments & Files

### Upload File

```http
POST /api/v1/attachments/upload
Content-Type: multipart/form-data
```

**Form Data:**
- `file`: File to upload
- `session_id`: Chat session ID (optional)
- `trip_id`: Trip ID (optional)

**Response:**
```json
{
  "id": "attachment_001",
  "filename": "flight_confirmation.pdf",
  "file_type": "application/pdf",
  "file_size": 1024000,
  "url": "https://storage.tripsage.ai/attachments/abc123.pdf",
  "created_at": "2025-01-16T10:00:00Z"
}
```

### Get Attachment

```http
GET /api/v1/attachments/{attachment_id}
```

### Delete Attachment

```http
DELETE /api/v1/attachments/{attachment_id}
```

## 📊 Analytics & Insights

### Trip Analytics

```http
GET /api/v1/trips/{trip_id}/analytics
```

### User Travel Insights

```http
GET /api/v1/users/insights
```

## 🚨 Error Responses

All endpoints return consistent error responses:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "departure_date",
      "issue": "Date must be in the future"
    },
    "request_id": "req_abc123"
  }
}
```

### Common Error Codes

- `VALIDATION_ERROR` (400): Invalid request data
- `AUTHENTICATION_ERROR` (401): Invalid or missing authentication
- `AUTHORIZATION_ERROR` (403): Insufficient permissions
- `NOT_FOUND` (404): Resource not found
- `RATE_LIMIT_EXCEEDED` (429): Too many requests
- `INTERNAL_ERROR` (500): Server error

## 📈 Rate Limiting

All endpoints are subject to rate limiting:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
X-RateLimit-Window: 3600
```

## 📝 Request/Response Examples

### Complete Trip Planning Flow

1. **Create Trip**
```bash
curl -X POST https://api.tripsage.ai/v1/trips \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "European Adventure",
    "start_date": "2025-06-01",
    "end_date": "2025-06-15",
    "destinations": [{"name": "Paris", "country": "France"}]
  }'
```

2. **Search Flights**
```bash
curl -G https://api.tripsage.ai/v1/flights/search \
  -H "Authorization: Bearer your-jwt-token" \
  -d origin=JFK \
  -d destination=CDG \
  -d departure_date=2025-06-01
```

3. **Share Trip**
```bash
curl -X POST https://api.tripsage.ai/v1/trips/123/share \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "user_emails": ["friend@example.com"],
    "permission_level": "edit"
  }'
```

---

*This documentation covers all REST API endpoints available in TripSage. For real-time features, see the [WebSocket API documentation](WEBSOCKET_API.md).*