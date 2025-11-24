# TripSage API Reference

Complete reference for the TripSage FastAPI endpoints. All endpoints require authentication via JWT tokens obtained through Supabase.

## Base URL

```text
https://api.tripsage.ai (production)
http://localhost:8000 (development)
```

## Authentication

> **⚠️ Legacy Python Backend API**  
> This document describes the legacy Python FastAPI backend endpoints.  
> **Authentication is now handled by the Next.js frontend via Supabase SSR routes (`/auth/*`).**  
> The Python backend middleware validates JWT tokens but does not provide auth endpoints.

All endpoints require a Bearer JWT token obtained through Supabase authentication:

```http
Authorization: Bearer <jwt_token>
```

**Frontend Auth Routes (Next.js):**

- `POST /auth/login` - Email/password login
- `POST /auth/register` - User registration
- `GET /auth/callback` - OAuth callback handler
- `POST /auth/logout` - Logout and session cleanup
- `GET /auth/confirm` - Email confirmation

## Health & System

### Health Check

```http
GET /api/health
```

Response:

```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "version": "1.0.0",
  "environment": "development"
}
```

## Trip Management

### Create Trip

```http
POST /api/trips/
```

Request:

```json
{
  "name": "Summer Vacation",
  "description": "Family trip to Europe",
  "start_date": "2025-07-01",
  "end_date": "2025-07-15",
  "budget": {
    "currency": "USD",
    "total_amount": 5000
  },
  "destinations": [
    {
      "name": "Paris",
      "coordinates": {"lat": 48.8566, "lng": 2.3522}
    }
  ]
}
```

### Get Trip

```http
GET /api/trips/{trip_id}
```

### List Trips

```http
GET /api/trips/
```

Query parameters:

- `skip`: Number of trips to skip (pagination)
- `limit`: Maximum number of trips to return
- `search`: Search term for trip names
- `type`: Filter by trip type
- `visibility`: Filter by visibility

### Update Trip

```http
PUT /api/trips/{trip_id}
```

### Delete Trip

```http
DELETE /api/trips/{trip_id}
```

### Trip Summary

```http
GET /api/trips/{trip_id}/summary
```

### Update Trip Preferences

```http
PUT /api/trips/{trip_id}/preferences
```

### Search Trips

```http
GET /api/trips/search
```

### Trip Suggestions

```http
GET /api/trips/suggestions
```

### Trip Itinerary

```http
GET /api/trips/{trip_id}/itinerary
```

### Export Trip

```http
POST /api/trips/{trip_id}/export
```

Request:

```json
{
  "format": "pdf",
  "include_costs": true
}
```

### Share Trip

```http
POST /api/trips/{trip_id}/share
```

### List Trip Collaborators

```http
GET /api/trips/{trip_id}/collaborators
```

### Update Collaborator Permissions

```http
PUT /api/trips/{trip_id}/collaborators/{user_id}
```

### Remove Collaborator

```http
DELETE /api/trips/{trip_id}/collaborators/{user_id}
```

## AI Agent Endpoints (Frontend)

Flight and accommodation operations are handled by frontend-only AI agents implemented with Vercel AI SDK v6. These endpoints stream UI-compatible responses and use tool calling for search operations.

### Flight Agent

```http
POST /api/agents/flights
```

Streams flight search results using AI SDK v6 ToolLoopAgent with tool calling.

Request:

```json
{
  "origin": "JFK",
  "destination": "CDG",
  "departureDate": "2025-07-01",
  "returnDate": "2025-07-15",
  "passengers": 2,
  "cabinClass": "economy"
}
```

Response: Streaming UI message stream (SSE) with tool calls and structured flight offers.

**Features:**

- BYOK provider resolution (OpenAI, Anthropic, xAI, etc.)
- Upstash Redis caching and rate limiting
- Tool-based flight search via Duffel integration
- AI Elements card rendering (`flight.v1` schema)

### Accommodation Agent

```http
POST /api/agents/accommodations
```

Streams accommodation search results using AI SDK v6 ToolLoopAgent with tool calling.

Request:

```json
{
  "location": "Paris",
  "checkIn": "2025-07-01",
  "checkOut": "2025-07-15",
  "guests": 2,
  "propertyType": "hotel"
}
```

Response: Streaming UI message stream (SSE) with tool calls and structured accommodation listings.

**Features:**

- BYOK provider resolution
- Upstash Redis caching and rate limiting
- Tool-based accommodation search
- AI Elements card rendering (`stay.v1` schema)

**Note:** Legacy Python endpoints (`/api/flights/*` and `/api/accommodations/*`) have been removed. All flight and accommodation operations are now handled by the frontend AI agents.

## Activities

Activity search and booking via Google Places API (New) with optional AI/web fallback. See SPEC-0030 and ADR-0053 for architecture details.

### Search Activities

```http
POST /api/activities/search
```

Search for activities (tours, experiences, attractions) by destination, category, date, and filters.

**Request Body:**

```json
{
  "destination": "Paris",
  "category": "museums",
  "date": "2025-06-15",
  "adults": 2,
  "children": 1,
  "infants": 0,
  "duration": {
    "min": 60,
    "max": 240
  },
  "difficulty": "easy",
  "indoor": true
}
```

**Parameters:**

- `destination` (string, required): Destination location name
- `category` (string, optional): Activity category (e.g., "museums", "tours", "parks")
- `date` (string, optional): ISO date string (YYYY-MM-DD)
- `adults` (number, optional): Number of adults (1-20)
- `children` (number, optional): Number of children (0-20)
- `infants` (number, optional): Number of infants (0-20)
- `duration` (object, optional): Duration range in minutes
  - `min` (number, optional): Minimum duration
  - `max` (number, optional): Maximum duration
- `difficulty` (string, optional): One of "easy", "moderate", "challenging", "extreme"
- `indoor` (boolean, optional): Filter for indoor activities

**Response:**

```json
{
  "activities": [
    {
      "id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
      "name": "Museum of Modern Art",
      "description": "A great museum experience",
      "location": "11 W 53rd St, New York, NY 10019",
      "coordinates": {
        "lat": 40.7614,
        "lng": -73.9776
      },
      "rating": 4.6,
      "price": 2,
      "type": "museum",
      "duration": 120,
      "date": "2025-06-15",
      "images": ["https://..."]
    }
  ],
  "metadata": {
    "total": 10,
    "cached": false,
    "primarySource": "googleplaces",
    "sources": ["googleplaces"],
    "notes": []
  }
}
```

**Rate Limit:** 20 requests per minute

**Authentication:** Optional (anonymous searches allowed)

### Get Activity Details

```http
GET /api/activities/[id]
```

Retrieve comprehensive details for a specific activity by its Google Place ID.

**Path Parameters:**

- `id` (string, required): Google Place ID

**Response:**

```json
{
  "id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
  "name": "Museum of Modern Art",
  "description": "A great museum experience with modern art collections",
  "location": "11 W 53rd St, New York, NY 10019",
  "coordinates": {
    "lat": 40.7614,
    "lng": -73.9776
  },
  "rating": 4.6,
  "price": 2,
  "type": "museum",
  "duration": 120,
  "date": "2025-06-15",
  "images": ["https://..."]
}
```

**Rate Limit:** 30 requests per minute

**Authentication:** Optional (anonymous access allowed)

**Note:** Legacy endpoints (`POST /api/activities/`, `GET /api/activities/`, `DELETE /api/activities/{activity_id}`) are not implemented. Activity saving and management are handled via the frontend UI and Supabase directly.

## Itineraries

**Note**: Destination and search endpoints have been migrated to frontend AI SDK v6 agents. See `/api/agents/destinations` and `/api/agents/flights` for the new implementation.

### Create Itinerary

```http
POST /api/itineraries/
```

### List Itineraries

```http
GET /api/itineraries/
```

### Search Itineraries

```http
GET /api/itineraries/search
```

### Get Itinerary

```http
GET /api/itineraries/{itinerary_id}
```

### Update Itinerary

```http
PUT /api/itineraries/{itinerary_id}
```

### Delete Itinerary

```http
DELETE /api/itineraries/{itinerary_id}
```

### Add Itinerary Item

```http
POST /api/itineraries/{itinerary_id}/items
```

### Get Itinerary Item

```http
GET /api/itineraries/{itinerary_id}/items/{item_id}
```

### Update Itinerary Item

```http
PUT /api/itineraries/{itinerary_id}/items/{item_id}
```

### Delete Itinerary Item

```http
DELETE /api/itineraries/{itinerary_id}/items/{item_id}
```

### Check Itinerary Conflicts

```http
GET /api/itineraries/{itinerary_id}/conflicts
```

### Optimize Itinerary

```http
POST /api/itineraries/{itinerary_id}/optimize
```

## Memory System

### Add Conversation Memory

```http
POST /api/memory/conversation
```

Request:

```json
{
  "session_id": "session-uuid",
  "content": "User prefers budget options",
  "metadata": {
    "context": "flightSearch",
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

### Get User Context

```http
GET /api/memory/context/{session_id}
```

### Search Memories

```http
GET /api/memory/search
```

Query parameters:

- `query`: Search term
- `session_id`: Filter by session
- `limit`: Maximum results

### Update Preferences

```http
PUT /api/memory/preferences
```

### Add Single Preference

```http
POST /api/memory/preferences
```

### Delete Memory

```http
DELETE /api/memory/{memory_id}
```

### Get Memory Stats

```http
GET /api/memory/stats
```

### Clear User Memory

```http
DELETE /api/memory/clear
```

## Attachments & Files

### Upload File

```http
POST /api/attachments/upload
```

Content-Type: `multipart/form-data`

### Batch Upload Files

```http
POST /api/attachments/upload/batch
```

### Get File Metadata

```http
GET /api/attachments/{file_id}
```

### Download File

```http
GET /api/attachments/{file_id}/download
```

### List Files

```http
GET /api/attachments/
```

Query parameters:

- `trip_id`: Filter by trip
- `file_type`: Filter by file type

### Delete File

```http
DELETE /api/attachments/{file_id}
```

### Get Trip Attachments

```http
GET /api/attachments/trip/{trip_id}
```

## Dashboard & Analytics

### System Overview

```http
GET /api/dashboard/overview
```

### Service Status

```http
GET /api/dashboard/services
```

### Usage Metrics

```http
GET /api/dashboard/metrics
```

### Rate Limit Status

```http
GET /api/dashboard/rate-limits
```

### System Alerts

```http
GET /api/dashboard/alerts
```

### Acknowledge Alert

```http
POST /api/dashboard/alerts/{alert_id}/acknowledge
```

### Delete Alert

```http
DELETE /api/dashboard/alerts/{alert_id}
```

### User Activity

```http
GET /api/dashboard/activity
```

### Trend Data

```http
GET /api/dashboard/trends
```

### Analytics Summary

```http
GET /api/dashboard/analytics
```

## User Management

### Get User Preferences

```http
GET /api/users/preferences
```

### Update User Preferences

```http
PUT /api/users/preferences
```

## Configuration

### List Agent Types

```http
GET /api/config/agents
```

### Get Agent Config

```http
GET /api/config/agents/{agent_type}
```

### Update Agent Config

```http
PUT /api/config/agents/{agent_type}
```

### List Config Versions

```http
GET /api/config/versions
```

### Rollback Config

```http
POST /api/config/rollback/{version_id}
```

### Environment Info

```http
GET /api/config/environment
```

## Error Handling

### Common HTTP Status Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request completed successfully |
| 201 | Created | Resource created successfully |
| 204 | No Content | Request successful, no content returned |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation errors |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |

### Error Response Format

```json
{
  "error": true,
  "message": "Human-readable error description",
  "code": "MACHINE_READABLE_CODE",
  "type": "error_category",
  "request_id": "req_abc123",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## Rate Limiting

Default limits (requests per minute):

- Unauthenticated: 10
- JWT tokens: 100
- API keys: 200-1000 (based on tier)

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
Retry-After: 60 (when exceeded)
```

## Real-time Communication

TripSage uses Supabase Realtime with private channels and Row Level Security. No custom WebSocket endpoints are exposed.

### Channel Topics

- `user:{user_id}` - Per-user updates
- `session:{session_id}` - Chat session updates

### Client Setup

```typescript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(url, anonKey)

// Set auth token for private channels
supabase.realtime.setAuth(accessToken)

// Join private channel
const channel = supabase.channel(`session:${sessionId}`, {
  config: { private: true }
})

channel.on('broadcast', { event: 'chat:message' }, (payload) => {
  console.log('Message received:', payload)
})

channel.subscribe()
```

## Client Integration Examples

### JavaScript/TypeScript

```javascript
// Initialize client
const TRIPSAGE_API_URL = 'https://api.tripsage.ai';
const API_KEY = 'your-api-key';

// Create trip
async function createTrip(tripData) {
  const response = await fetch(`${TRIPSAGE_API_URL}/api/trips/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY
    },
    body: JSON.stringify(tripData)
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// Search flights using frontend agent endpoint
async function searchFlights(searchParams) {
  const response = await fetch(`${TRIPSAGE_API_URL}/api/agents/flights`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${JWT_TOKEN}`
    },
    body: JSON.stringify({
      origin: searchParams.origin,
      destination: searchParams.destination,
      departureDate: searchParams.departure_date,
      returnDate: searchParams.return_date,
      passengers: searchParams.passengers,
      cabinClass: searchParams.cabin_class
    })
  });

  // Response is a streaming UI message stream (SSE)
  return response;
}
```

### Python

```python
import requests
import json

class TripSageClient:
    def __init__(self, api_key, base_url='https://api.tripsage.ai'):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        })

    def create_trip(self, trip_data):
        """Create a new trip"""
        response = self.session.post(f'{self.base_url}/api/trips/', json=trip_data)
        response.raise_for_status()
        return response.json()

    def search_flights(self, search_params):
        """Search for flights using frontend agent endpoint"""
        # Note: This endpoint streams SSE responses
        # For Python clients, use a streaming HTTP client or the frontend API
        response = self.session.post(
            f'{self.base_url}/api/agents/flights',
            json={
                'origin': search_params.get('origin'),
                'destination': search_params.get('destination'),
                'departureDate': search_params.get('departure_date'),
                'returnDate': search_params.get('return_date'),
                'passengers': search_params.get('passengers', 1),
                'cabinClass': search_params.get('cabin_class', 'economy')
            },
            headers={'Authorization': f'Bearer {self.jwt_token}'}
        )
        response.raise_for_status()
        # Returns streaming response - handle accordingly
        return response

    def get_trip(self, trip_id):
        """Get trip details"""
        response = self.session.get(f'{self.base_url}/api/trips/{trip_id}')
        response.raise_for_status()
        return response.json()

# Usage
client = TripSageClient('your-api-key')
trip = client.create_trip({
    'name': 'Summer Vacation',
    'start_date': '2025-07-01',
    'end_date': '2025-07-15',
    'budget': {'currency': 'USD', 'total_amount': 3000}
})
```

### cURL Examples

```bash
# Create trip
curl -X POST "https://api.tripsage.ai/api/trips/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "name": "Summer Vacation",
    "start_date": "2025-07-01",
    "end_date": "2025-07-15",
    "budget": {"currency": "USD", "total_amount": 3000}
  }'

# Search flights using frontend agent endpoint (streaming SSE)
curl -X POST "https://api.tripsage.ai/api/agents/flights" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-jwt-token" \
  -d '{
    "origin": "JFK",
    "destination": "CDG",
    "departureDate": "2025-07-01",
    "returnDate": "2025-07-15",
    "passengers": 2,
    "cabinClass": "economy"
  }'

# Get trip details
curl -X GET "https://api.tripsage.ai/api/trips/123" \
  -H "X-API-Key: your-api-key"
```

## Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`
