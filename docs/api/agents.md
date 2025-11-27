# AI Agents

All agent endpoints return Server-Sent Events (SSE) streams using AI SDK v6 UI message format. Responses are streamed in real-time.

## Streaming Overview

Agent endpoints use Server-Sent Events (SSE) for streaming responses. The stream contains AI SDK v6 UI messages that can be consumed using `ReadableStream`/`EventSource` in JavaScript or an SSE-capable library in other languages.

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
| `cabinClass` | string | No | Cabin class (`economy`, `premium_economy`, `business`, `first`, default: `economy`) |
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
**Response**: `text/event-stream` (SSE)

### Request Body

Similar to flight search, with accommodation-specific parameters including location, check-in/check-out dates, guests, and property preferences.

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

Destination research parameters including interests, travel style, budget, and time of year preferences.

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

Itinerary planning parameters including destination, duration, interests, and pace preferences.

### Response

`200 OK` - SSE stream with itinerary suggestions

### Errors

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## `POST /api/agents/budget`

Budget planning agent.

**Authentication**: Required  
**Rate Limit Key**: `agents:budget`  
**Response**: `text/event-stream` (SSE)

### Request Body

Budget planning parameters including destination, duration, travel style, and spending categories.

### Response

`200 OK` - SSE stream with budget analysis

### Errors

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## `POST /api/agents/memory`

Conversational memory agent.

**Authentication**: Required  
**Rate Limit Key**: `agents:memory`  
**Response**: `text/event-stream` (SSE)

### Request Body

Memory query parameters for context-aware responses.

### Response

`200 OK` - SSE stream with memory-enhanced responses

### Errors

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## `POST /api/agents/router`

Intent router agent that directs user queries to the appropriate specialized agent.

**Authentication**: Required  
**Rate Limit Key**: `agents:router`  
**Response**: `text/event-stream` (SSE)

### Request Body

User intent/message to be routed.

### Response

`200 OK` - SSE stream with routed intent response

### Errors

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## `POST /api/ai/stream`

Generic AI stream route used in demos/tests.

**Authentication**: Required  
**Rate Limit Key**: `ai:stream`  
**Response**: `text/event-stream` (SSE)

### Request Body

Generic AI stream parameters.

### Response

`200 OK` - SSE stream
