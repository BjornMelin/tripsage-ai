# Trips

Trip management and itinerary endpoints.

## `GET /api/trips`

List trips for the authenticated user with optional filtering.

**Authentication**: Required  
**Rate Limit Key**: `trips:list`

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `destination` | string | No | Filter by destination (partial match) |
| `status` | string | No | Filter by status (`planning`, `confirmed`, `completed`, `cancelled`) |
| `startDate` | string | No | Filter trips starting on or after this date (YYYY-MM-DD) |
| `endDate` | string | No | Filter trips ending on or before this date (YYYY-MM-DD) |

### Response

`200 OK`

```json
[
  {
    "id": "1",
    "title": "Summer Vacation",
    "destination": "Paris",
    "startDate": "2025-07-01",
    "endDate": "2025-07-15",
    "travelers": 2,
    "budget": 3000,
    "currency": "USD",
    "status": "planning",
    "tripType": "leisure",
    "visibility": "private",
    "createdAt": "2025-01-15T10:00:00Z",
    "updatedAt": "2025-01-15T10:00:00Z"
  }
]
```

### Errors

- `401` - Not authenticated
- `429` - Rate limit exceeded

### Example

```typescript
const response = await fetch("http://localhost:3000/api/trips?status=planning", {
  headers: {
    Cookie: `sb-access-token=${jwtToken}`,
  },
});
const trips = await response.json();
```

---

## `POST /api/trips`

Create a new trip for the authenticated user.

**Authentication**: Required  
**Rate Limit Key**: `trips:create`

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Trip title (max 200 chars) |
| `destination` | string | Yes | Destination name (max 200 chars) |
| `startDate` | string | Yes | Start date (YYYY-MM-DD) |
| `endDate` | string | Yes | End date (YYYY-MM-DD) |
| `travelers` | number | No | Number of travelers (default: 1) |
| `budget` | number | No | Budget amount |
| `currency` | string | No | ISO currency code (default: "USD") |
| `status` | string | No | Trip status (default: "planning") |
| `tripType` | string | No | Trip type (default: "leisure") |
| `visibility` | string | No | Visibility level (default: "private") |
| `tags` | string[] | No | Trip tags (max 50) |
| `description` | string | No | Trip description (max 1000 chars) |
| `preferences` | object | No | Trip preferences object |

### Response

`201 Created`

```json
{
  "id": "1",
  "title": "Summer Vacation",
  "destination": "Paris",
  "startDate": "2025-07-01",
  "endDate": "2025-07-15",
  "travelers": 2,
  "budget": 3000,
  "currency": "USD",
  "status": "planning",
  "tripType": "leisure",
  "visibility": "private",
  "createdAt": "2025-01-15T10:00:00Z",
  "updatedAt": "2025-01-15T10:00:00Z"
}
```

### Errors

- `400` - Validation failed (check `issues` array)
- `401` - Not authenticated
- `429` - Rate limit exceeded

### Example

```python
import requests

response = requests.post(
    "http://localhost:3000/api/trips",
    cookies={"sb-access-token": jwt_token},
    json={
        "title": "Summer Vacation",
        "destination": "Paris",
        "startDate": "2025-07-01",
        "endDate": "2025-07-15",
        "travelers": 2,
        "budget": 3000,
        "currency": "USD"
    }
)
trip = response.json()
```

---

## `GET /api/trips/{id}`

Get a specific trip by ID.

**Authentication**: Required  
**Rate Limit Key**: `trips:list`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Trip ID |

### Response

`200 OK`

```json
{
  "id": "1",
  "title": "Summer Vacation",
  "destination": "Paris",
  "startDate": "2025-07-01",
  "endDate": "2025-07-15",
  "travelers": 2,
  "budget": 3000,
  "currency": "USD",
  "status": "planning",
  "tripType": "leisure",
  "visibility": "private",
  "createdAt": "2025-01-15T10:00:00Z",
  "updatedAt": "2025-01-15T10:00:00Z"
}
```

### Errors

- `401` - Not authenticated
- `404` - Trip not found
- `429` - Rate limit exceeded

### Example

```bash
curl -X GET "http://localhost:3000/api/trips/1" \
  --cookie "sb-access-token=$JWT"
```

---

## `PUT /api/trips/{id}`

Update a trip (partial update supported).

**Authentication**: Required
**Rate Limit Key**: `trips:update`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Trip ID |

### Request Body

Same fields as `POST /api/trips`, all optional.

### Response

`200 OK` - Returns updated trip object

### Errors

- `400` - Validation failed
- `401` - Not authenticated
- `404` - Trip not found
- `429` - Rate limit exceeded

### Example

```typescript
const response = await fetch("http://localhost:3000/api/trips/1", {
  method: "PUT",
  headers: {
    "Content-Type": "application/json",
    Cookie: `sb-access-token=${jwtToken}`,
  },
  body: JSON.stringify({
    destination: "Rome",
    title: "Updated Trip"
  }),
});
```

---

## `DELETE /api/trips/{id}`

Delete a trip.

**Authentication**: Required
**Rate Limit Key**: `trips:delete`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Trip ID |

### Response

`204 No Content`

### Errors

- `401` - Not authenticated
- `404` - Trip not found
- `429` - Rate limit exceeded

### Example

```bash
curl -X DELETE "http://localhost:3000/api/trips/1" \
  --cookie "sb-access-token=$JWT"
```

---

## `GET /api/trips/suggestions`

Get AI-generated trip suggestions.

**Authentication**: Required  
**Rate Limit Key**: `trips:suggestions`

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | number | No | Maximum number of suggestions (default: 10) |
| `budgetMax` | number | No | Maximum budget filter |
| `category` | string | No | Category filter (`adventure`, `relaxation`, `culture`, `nature`, `city`, `beach`) |

### Response

`200 OK`

```json
[
  {
    "id": "suggestion-1",
    "title": "Romantic Paris Getaway",
    "destination": "Paris, France",
    "description": "Experience the City of Light...",
    "estimatedPrice": 2500,
    "currency": "USD",
    "duration": 7,
    "category": "culture",
    "rating": 4.8,
    "highlights": ["Eiffel Tower", "Louvre Museum", "Seine River Cruise"],
    "bestTimeToVisit": "April to June, September to October"
  }
]
```

### Errors

- `401` - Not authenticated
- `429` - Rate limit exceeded

### Examples

**cURL**

```bash
curl -X GET "http://localhost:3000/api/trips/suggestions?limit=5&category=culture" \
  --cookie "sb-access-token=$JWT"
```

**TypeScript/Fetch**

```typescript
const response = await fetch(
  "http://localhost:3000/api/trips/suggestions?limit=5&category=culture&budgetMax=5000",
  {
    headers: {
      Cookie: `sb-access-token=${jwtToken}`,
    },
  }
);
const suggestions = await response.json();
suggestions.forEach(suggestion => {
  console.log(`${suggestion.title} - $${suggestion.estimatedPrice}`);
});
```

**Python/Requests**

```python
import requests

response = requests.get(
    "http://localhost:3000/api/trips/suggestions",
    cookies={"sb-access-token": jwt_token},
    params={
        "limit": 5,
        "category": "adventure",
        "budgetMax": 5000
    }
)
suggestions = response.json()
for suggestion in suggestions:
    print(f"{suggestion['title']} - ${suggestion['estimatedPrice']}")
```

---

## Itineraries

### `GET /api/itineraries`

List itinerary items with optional trip filter.

**Authentication**: Required  
**Rate Limit Key**: `itineraries:list`

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tripId` | string | No | Filter by trip ID (numeric string, e.g., `?tripId=123`) |

#### Response

`200 OK`

```json
[
  {
    "id": "1",
    "tripId": 1,
    "title": "Louvre Museum Visit",
    "itemType": "activity",
    "startTime": "2025-07-02T10:00:00Z",
    "endTime": "2025-07-02T14:00:00Z",
    "location": "Paris, France",
    "price": 25,
    "currency": "USD",
    "bookingStatus": "planned",
    "description": "Guided tour of the Louvre"
  }
]
```

#### Errors

- `401` - Not authenticated
- `429` - Rate limit exceeded

#### Examples

**cURL - List all itineraries**

```bash
curl -X GET "http://localhost:3000/api/itineraries" \
  --cookie "sb-access-token=$JWT"
```

**cURL - Filter by trip ID**

```bash
curl -X GET "http://localhost:3000/api/itineraries?tripId=123" \
  --cookie "sb-access-token=$JWT"
```

**TypeScript/Fetch - List all itineraries**

```typescript
const response = await fetch("http://localhost:3000/api/itineraries", {
  headers: {
    Cookie: `sb-access-token=${jwtToken}`,
  },
});
const itineraries = await response.json();
console.log(`Found ${itineraries.length} itinerary items`);
```

**TypeScript/Fetch - Filter by trip ID**

```typescript
const response = await fetch("http://localhost:3000/api/itineraries?tripId=123", {
  headers: {
    Cookie: `sb-access-token=${jwtToken}`,
  },
});
const itineraries = await response.json();
itineraries.forEach(item => {
  console.log(`${item.title} - ${item.itemType}`);
});
```

**Python/Requests - List all itineraries**

```python
import requests

response = requests.get(
    "http://localhost:3000/api/itineraries",
    cookies={"sb-access-token": jwt_token}
)
itineraries = response.json()
print(f"Found {len(itineraries)} itinerary items")
```

**Python/Requests - Filter by trip ID**

```python
import requests

response = requests.get(
    "http://localhost:3000/api/itineraries",
    cookies={"sb-access-token": jwt_token},
    params={"tripId": "123"}
)
itineraries = response.json()
for item in itineraries:
    print(f"{item['title']} - {item['itemType']}")
```

---

### `POST /api/itineraries`

Create a new itinerary item.

**Authentication**: Required  
**Rate Limit Key**: `itineraries:create`

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tripId` | number | Yes | Trip ID (JSON number type, parsed as integer on server) |
| `title` | string | Yes | Item title (max 200 chars) |
| `itemType` | string | Yes | Item type (`activity`, `meal`, `transport`, `accommodation`, `event`, `other`) |
| `startTime` | string | No | Start time (ISO 8601) |
| `endTime` | string | No | End time (ISO 8601) |
| `location` | string | No | Location string |
| `price` | number | No | Price amount |
| `currency` | string | No | ISO currency code (default: "USD") |
| `description` | string | No | Description (max 1000 chars) |
| `bookingStatus` | string | No | Booking status (default: "planned") |
| `metadata` | object | No | Additional metadata |

#### Response

`201 Created` - Returns created itinerary item

#### Errors

- `400` - Validation failed
- `401` - Not authenticated
- `403` - Trip not owned by user
- `429` - Rate limit exceeded

#### Example

```bash
curl -X POST "http://localhost:3000/api/itineraries" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "tripId": 1,
    "title": "Louvre Museum",
    "itemType": "activity",
    "startTime": "2025-07-02T10:00:00Z",
    "price": 25,
    "currency": "USD"
  }'
```
