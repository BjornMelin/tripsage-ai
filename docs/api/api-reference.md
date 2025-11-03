# TripSage API Reference

Complete reference for the TripSage FastAPI endpoints. All endpoints require authentication via JWT tokens obtained through Supabase.

## Base URL

```text
https://api.tripsage.ai (production)
http://localhost:8000 (development)
```

## Authentication

All endpoints require a Bearer JWT token obtained through Supabase authentication:

```http
Authorization: Bearer <jwt_token>
```

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

### User Registration

```http
POST /api/auth/register
```

**Note**: Registration is handled by Supabase. Use Supabase client SDK or hosted UI.

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

## Flight Operations

### Search Flights

```http
POST /api/flights/search
```

Request:

```json
{
  "origin": "JFK",
  "destination": "CDG",
  "departure_date": "2025-07-01",
  "return_date": "2025-07-15",
  "passengers": 2,
  "cabin_class": "economy"
}
```

### Get Flight Details

```http
GET /api/flights/{flight_id}
```

### Book Flight

```http
POST /api/flights/{flight_id}/book
```

### List Flight Bookings

```http
GET /api/flights/bookings
```

## Accommodation Operations

### Search Accommodations

```http
POST /api/accommodations/search
```

Request:

```json
{
  "location": "Paris",
  "check_in": "2025-07-01",
  "check_out": "2025-07-15",
  "guests": 2,
  "room_type": "double"
}
```

### Get Accommodation Details

```http
GET /api/accommodations/{accommodation_id}
```

### Book Accommodation

```http
POST /api/accommodations/{accommodation_id}/book
```

## Activities

### Search Activities

```http
GET /api/activities/search
```

Query parameters:

- `location`: Location name or coordinates
- `categories`: Comma-separated activity categories
- `date`: Specific date filter
- `budget`: Maximum price per person

### Save Activity

```http
POST /api/activities/
```

### List Saved Activities

```http
GET /api/activities/
```

### Get Activity Details

```http
GET /api/activities/{activity_id}
```

### Delete Saved Activity

```http
DELETE /api/activities/{activity_id}
```

## Destinations

### Search Destinations

```http
GET /api/destinations/search
```

Query parameters:

- `query`: Search term
- `limit`: Maximum results

### Save Destination

```http
POST /api/destinations/
```

### List Saved Destinations

```http
GET /api/destinations/
```

### Get Destination Details

```http
GET /api/destinations/{destination_id}
```

## Itineraries

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
    "context": "flight_search",
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

## Unified Search

### Unified Search Endpoint

```http
GET /api/search/
```

Query parameters:

- `query`: Search term
- `types`: Comma-separated entity types (trips,flights,accommodations)
- `limit`: Maximum results per type

### Get Search Suggestions

```http
GET /api/search/suggestions
```

### Get Recent Searches

```http
GET /api/search/recent
```

### Save Search

```http
POST /api/search/save
```

### Delete Saved Search

```http
DELETE /api/search/{search_id}
```

### Bulk Search

```http
POST /api/search/bulk
```

### Search Analytics

```http
GET /api/search/analytics
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

// Search flights
async function searchFlights(searchParams) {
  const response = await fetch(`${TRIPSAGE_API_URL}/api/flights/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY
    },
    body: JSON.stringify(searchParams)
  });

  return response.json();
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
        """Search for flights"""
        response = self.session.post(f'{self.base_url}/api/flights/search', json=search_params)
        response.raise_for_status()
        return response.json()

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

# Search flights
curl -X POST "https://api.tripsage.ai/api/flights/search" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "origin": "JFK",
    "destination": "CDG",
    "departure_date": "2025-07-01",
    "passengers": 2
  }'

# Get trip details
curl -X GET "https://api.tripsage.ai/api/trips/123" \
  -H "X-API-Key: your-api-key"
```

## Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`
