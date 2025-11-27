# AI Agents

All agent endpoints return Server-Sent Events (SSE) streams using AI SDK v6 UI message format. Responses are streamed in real-time.

## Streaming Overview

Agent endpoints use Server-Sent Events (SSE) for streaming responses. The stream contains AI SDK v6 UI messages that can be consumed using `ReadableStream`/`EventSource` in JavaScript or an SSE-capable library in other languages.

**Authentication Note**: All agent endpoints require authentication. Use the `sb-access-token` cookie (Supabase default cookie name) or pass the JWT token via `Authorization: Bearer <token>` header.

### TypeScript Example

```typescript
const response = await fetch("http://localhost:3000/api/agents/flights", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Cookie: `sb-access-token=${jwtToken}`,
  },
  body: JSON.stringify({
    origin: "JFK",
    destination: "CDG",
    departureDate: "2025-07-01",
  }),
});

const reader = response.body?.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const chunk = decoder.decode(value);
  // Process SSE messages
}
```

### Python Example

**Note**: This example requires the external `sseclient-py` library. Install it with: `pip install sseclient-py`

Alternatively, you can use standard library with manual SSE parsing using `requests` and `urllib`.

```python
import requests
import sseclient

response = requests.post(
    "http://localhost:3000/api/agents/flights",
    cookies={"sb-access-token": jwt_token},
    json={
        "origin": "JFK",
        "destination": "CDG",
        "departureDate": "2025-07-01"
    },
    stream=True
)

client = sseclient.SSEClient(response)
for event in client.events():
    print(event.data)
```

---

## `POST /api/agents/flights`

Streaming flight search agent.

**Authentication**: Required  
**Rate Limit Key**: `agents:flight`  
**Content-Type**: `application/json`  
**Response**: `text/event-stream` (SSE)

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `origin` | string | Yes | Origin airport IATA code (min 3 chars) |
| `destination` | string | Yes | Destination airport IATA code (min 3 chars) |
| `departureDate` | string | Yes | Departure date (YYYY-MM-DD) |
| `returnDate` | string | No | Return date (YYYY-MM-DD) |
| `passengers` | number | No | Passenger count (default: 1) |
| `cabinClass` | string | No | Cabin class: `economy`, `premium_economy`, `business`, `first` (default: `economy`) |
| `currency` | string | No | ISO currency code (default: "USD") |
| `nonstop` | boolean | No | Require nonstop flights only (default: false) |

### Response

`200 OK` - SSE stream with flight search results

### Errors

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded

### Example

```bash
curl -N -X POST "http://localhost:3000/api/agents/flights" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "JFK",
    "destination": "CDG",
    "departureDate": "2025-07-01",
    "returnDate": "2025-07-15",
    "passengers": 2,
    "cabinClass": "economy"
  }'
```

---

## `POST /api/agents/accommodations`

Streaming accommodation search agent.

**Authentication**: Required  
**Rate Limit Key**: `agents:accommodations`  
**Content-Type**: `application/json`  
**Response**: `text/event-stream` (SSE)

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `location` | string/object | Yes | Location string or geocoordinates {latitude, longitude} |
| `checkIn` | string | Yes | Check-in date (YYYY-MM-DD) |
| `checkOut` | string | Yes | Check-out date (YYYY-MM-DD) |
| `guests` | object | Yes | Guest composition {adults: number, children: number (optional)} |
| `rooms` | number | No | Number of rooms (default: 1) |
| `roomPreferences` | array | No | Preferences: bed_type, smoking_allowed, non_smoking |
| `amenities` | array | No | Required amenities (e.g., "wifi", "parking", "gym") |
| `priceRange` | object | No | Budget constraints {min: number, max: number} |
| `currency` | string | No | ISO currency code (default: "USD") |
| `propertyTypes` | array | No | Filter by type: hotel, apartment, villa, hostel, etc. |
| `starRating` | object | No | Star rating filter {min: number, max: number} |
| `flexibleDates` | boolean | No | Allow flexible dates (default: false) |
| `accessibilityNeeds` | array | No | Accessibility requirements |
| `cancellationPolicy` | string | No | Preferred cancellation policy |
| `sortBy` | string | No | Sort results: price, rating, distance, popularity |
| `limit` | number | No | Maximum results (default: 10) |

### Response

`200 OK` - SSE stream with accommodation search results

### Errors

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## `POST /api/agents/destinations`

Destination research agent.

**Authentication**: Required  
**Rate Limit Key**: `agents:destinations`  
**Response**: `text/event-stream` (SSE)

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `interests` | array | Yes | Array of interests: adventure, culture, relaxation, nature, food, history, shopping, family, beach, mountain |
| `travelStyle` | string | No | Travel style: relaxation, adventure, culture, family (default: balanced) |
| `budget` | object/string | No | Budget constraints: {min: number, max: number} or "low"/"medium"/"high" |
| `timeOfYear` | string | No | Preferred time: "spring", "summer", "fall", "winter" or month range "Apr-Jun" |
| `duration` | object/number | No | Trip duration: {minDays: number, maxDays: number} or single number for days |
| `party` | object | No | Traveling party: {adults: number, children: number, seniors: number} |
| `includeDestinations` | array | No | Specific destinations to include |
| `excludeDestinations` | array | No | Specific destinations to exclude |
| `accommodationPreferences` | array | No | Preferred accommodation types: hotel, apartment, resort, etc. |
| `accessibilityNeeds` | array | No | Accessibility requirements |
| `languagePreferences` | array | No | Preferred languages ISO codes |
| `specialRequests` | string | No | Any special requests or notes |
| `maxResults` | number | No | Maximum destinations to return (default: 10) |
| `callbackUrl` | string | No | Optional webhook URL for async results |

### Response

`200 OK` - SSE stream with destination research results

### Errors

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## `POST /api/agents/itineraries`

Itinerary planning agent.

**Authentication**: Required  
**Rate Limit Key**: `agents:itineraries`  
**Response**: `text/event-stream` (SSE)

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `destination` | string | Yes | Destination name or coordinates {latitude, longitude} |
| `startDate` | string | No | Start date (YYYY-MM-DD) or ISO 8601 |
| `endDate` | string | No | End date (YYYY-MM-DD) or ISO 8601 |
| `durationDays` | number | No | Duration in days (use instead of startDate/endDate) |
| `travelers` | number | Yes | Number of travelers |
| `interests` | array | No | Array of interests for activity matching |
| `pace` | string | No | Travel pace: relaxed, moderate, busy (default: moderate) |
| `budget` | object/string | No | Daily or total budget: {currency: string, amount: number} or category |
| `accommodationPreferences` | array | No | Preferred accommodation types |
| `transportPreferences` | array | No | Preferred transport modes: car, train, bus, flight |
| `accessibilityRequirements` | string | No | Any accessibility needs |
| `language` | string | No | Language preference (ISO code) |
| `timezone` | string | No | Timezone for itinerary (default: destination timezone) |
| `maxSuggestions` | number | No | Maximum itinerary suggestions to return (default: 5) |
| `responseFormat` | string | No | Format: itinerary, day-by-day (default: itinerary) |

### Response

`200 OK` - SSE stream with itinerary suggestions

### Errors

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## `POST /api/agents/budget`

Budget planning agent that analyzes trip costs and provides spending breakdowns.

**Authentication**: Required
**Rate Limit Key**: `agents:budget`
**Content-Type**: `application/json`
**Response**: `text/event-stream` (SSE)

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `destination` | string | Yes | Destination name or location |
| `duration` | number | Yes | Trip duration in days |
| `travelers` | number | Yes | Number of travelers |
| `travelStyle` | string | No | Travel style: `budget`, `moderate`, `luxury` (default: `moderate`) |
| `currency` | string | No | ISO currency code (default: "USD") |
| `categories` | array | No | Spending categories to analyze: `accommodation`, `flights`, `food`, `activities`, `transportation`, `shopping`, `other` |
| `totalBudget` | number | No | Total budget amount for validation |
| `perDiemBudget` | number | No | Daily budget amount |
| `startDate` | string | No | Trip start date (YYYY-MM-DD) for seasonal pricing |
| `accommodationType` | string | No | Preferred accommodation type for cost estimates |
| `includeFlights` | boolean | No | Include flight costs in analysis (default: true) |

### Response

`200 OK` - SSE stream with budget analysis and spending recommendations

### Errors

- `400` - Invalid request parameters (missing required fields, invalid travelStyle, negative duration/travelers)
- `401` - Not authenticated
- `429` - Rate limit exceeded

### Example

```bash
curl -N -X POST "http://localhost:3000/api/agents/budget" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "Paris, France",
    "duration": 7,
    "travelers": 2,
    "travelStyle": "moderate",
    "currency": "USD",
    "categories": ["accommodation", "food", "activities", "transportation"],
    "totalBudget": 3000
  }'
```

---

## `POST /api/agents/memory`

Conversational memory agent that retrieves and utilizes user preferences and conversation history.

**Authentication**: Required
**Rate Limit Key**: `agents:memory`
**Content-Type**: `application/json`
**Response**: `text/event-stream` (SSE)

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | User query or message |
| `conversationId` | string | No | Conversation ID for context continuity |
| `userId` | string | No | User ID for personalized memory retrieval (auto-detected from auth if not provided) |
| `includePreferences` | boolean | No | Include user preferences in context (default: true) |
| `includePastTrips` | boolean | No | Include past trip history in context (default: true) |
| `maxMemoryItems` | number | No | Maximum memory items to retrieve (default: 10) |
| `memoryTypes` | array | No | Types of memory to retrieve: `preferences`, `trips`, `searches`, `conversations` |
| `timeRange` | object | No | Time range filter {from: ISO date, to: ISO date} |

### Response

`200 OK` - SSE stream with memory-enhanced responses including retrieved context

### Errors

- `400` - Invalid request parameters (missing query, invalid memoryTypes, malformed timeRange)
- `401` - Not authenticated
- `429` - Rate limit exceeded

### Example

```bash
curl -N -X POST "http://localhost:3000/api/agents/memory" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What were my favorite destinations from last year?",
    "conversationId": "conv-123",
    "includePreferences": true,
    "includePastTrips": true,
    "memoryTypes": ["preferences", "trips"]
  }'
```

---

## `POST /api/agents/router`

Intent router agent that analyzes user queries and routes them to the appropriate specialized agent (flights, accommodations, destinations, itineraries, budget, memory).

**Authentication**: Required
**Rate Limit Key**: `agents:router`
**Content-Type**: `application/json`
**Response**: `text/event-stream` (SSE)

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | User message or query to be analyzed and routed |
| `conversationId` | string | No | Conversation ID for context continuity |
| `context` | object | No | Additional context {location: string, previousIntent: string, sessionData: object} |
| `allowedAgents` | array | No | Restrict routing to specific agents: `flights`, `accommodations`, `destinations`, `itineraries`, `budget`, `memory` |
| `returnRoutingInfo` | boolean | No | Include routing decision metadata in response (default: false) |

### Response

`200 OK` - SSE stream with routed agent response

The response includes:

- Identified intent and selected agent
- Streamed response from the specialized agent
- Optional routing metadata (if `returnRoutingInfo: true`)

### Errors

- `400` - Invalid request parameters (missing message, invalid allowedAgents values, empty message)
- `401` - Not authenticated
- `429` - Rate limit exceeded

### Example

```bash
curl -N -X POST "http://localhost:3000/api/agents/router" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find me cheap flights to Tokyo next month",
    "conversationId": "conv-456",
    "returnRoutingInfo": true
  }'
```

---

## `POST /api/ai/stream`

Generic AI streaming endpoint for testing and demo purposes. Provides a simple streaming chat interface without specialized agent logic.

**Authentication**: Required
**Rate Limit Key**: `ai:stream`
**Content-Type**: `application/json`
**Response**: `text/event-stream` (SSE)

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `messages` | array | Yes | Array of messages {role: string, content: string} |
| `model` | string | No | Model name (default: system default) |
| `temperature` | number | No | Temperature 0-2 (default: 0.7) |
| `maxTokens` | number | No | Maximum tokens to generate |
| `stream` | boolean | No | Enable streaming (default: true) |

### Response

`200 OK` - SSE stream with AI-generated responses

### Errors

- `400` - Invalid request parameters (missing messages, invalid temperature range, malformed message objects)
- `401` - Not authenticated
- `429` - Rate limit exceeded

### Example

```bash
curl -N -X POST "http://localhost:3000/api/ai/stream" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "temperature": 0.7
  }'
```
