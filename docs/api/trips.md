# Trips

Trip management and itinerary endpoints.

## `GET /api/trips`

List trips the authenticated user can access (owned trips + trips shared with them) with optional filtering.

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
    "userId": "00000000-0000-0000-0000-000000000000",
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

Notes:

- `id` is returned as a string, but the `{id}` path parameter is numeric (e.g. `/api/trips/123`).
- `userId` is the trip owner (even when the trip is shared with you).
- `visibility` is derived: `"private"` for the owner and `"shared"` for collaborators.

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
**Rate Limit Key**: `trips:detail`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Trip ID (numeric string, e.g. `123`) |

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
- `403` - Insufficient permissions (e.g., viewer collaborator)
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
- `403` - Only the trip owner can delete a trip
- `404` - Trip not found
- `429` - Rate limit exceeded

### Example

```bash
curl -X DELETE "http://localhost:3000/api/trips/1" \
  --cookie "sb-access-token=$JWT"
```

---

## Trip Collaborators

Trip collaboration is managed through collaborator rows scoped to a trip ID. The trip
owner is derived from the trip record (`trip.userId`) and is not a collaborator row.

### Roles

- `viewer`: read-only access
- `editor`: can update trip details via `PUT /api/trips/{id}`
- `admin`: can update trip details via `PUT /api/trips/{id}`

Note: collaborator roles currently gate trip metadata updates. Other trip resources may have separate permission rules.

## `GET /api/trips/{id}/collaborators`

List collaborators for a trip.

**Authentication**: Required  
**Rate Limit Key**: `trips:collaborators:list`

### Response

`200 OK`

```json
{
  "tripId": 123,
  "ownerId": "00000000-0000-0000-0000-000000000000",
  "isOwner": true,
  "collaborators": [
    {
      "id": 1,
      "tripId": 123,
      "userId": "11111111-1111-1111-1111-111111111111",
      "userEmail": "collab@example.com",
      "role": "viewer",
      "createdAt": "2025-01-15T10:00:00Z"
    }
  ]
}
```

Notes:

- `userEmail` is only populated for the trip owner (all collaborators). Non-owners only see their own email.

### Errors

- `401` - Not authenticated
- `404` - Trip not found (or you do not have access)
- `429` - Rate limit exceeded

---

## `POST /api/trips/{id}/collaborators`

Invite/add a collaborator (owner-only). If the email does not match an existing Supabase Auth user, an invite email is sent first.

**Authentication**: Required  
**Rate Limit Key**: `trips:collaborators:invite`

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | Email address to invite |
| `role` | string | No | `viewer` \| `editor` \| `admin` (default: `viewer`) |

### Response

`201 Created`

```json
{
  "invited": true,
  "collaborator": {
    "id": 1,
    "tripId": 123,
    "userId": "11111111-1111-1111-1111-111111111111",
    "userEmail": "collab@example.com",
    "role": "viewer",
    "createdAt": "2025-01-15T10:00:00Z"
  }
}
```

### Errors

- `400` - Validation failed or invalid request
- `401` - Not authenticated
- `403` - Only the trip owner can invite collaborators
- `409` - User is already a collaborator on this trip
- `429` - Rate limit exceeded

---

## `PATCH /api/trips/{id}/collaborators/{userId}`

Update a collaborator role (owner-only).

**Authentication**: Required  
**Rate Limit Key**: `trips:collaborators:update`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Trip ID (numeric string, e.g. `123`) |
| `userId` | string | Yes | Collaborator user ID (UUID) |

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role` | string | Yes | `viewer` \| `editor` \| `admin` |

### Response

`200 OK`

```json
{
  "collaborator": {
    "id": 1,
    "tripId": 123,
    "userId": "11111111-1111-1111-1111-111111111111",
    "role": "editor",
    "createdAt": "2025-01-15T10:00:00Z"
  }
}
```

### Errors

- `400` - Invalid request (e.g., userId is not a UUID)
- `401` - Not authenticated
- `403` - Only the trip owner can update collaborator roles
- `404` - Trip or collaborator not found
- `429` - Rate limit exceeded

---

## `DELETE /api/trips/{id}/collaborators/{userId}`

Remove a collaborator. Trip owners can remove any collaborator. Collaborators can remove themselves (leave the trip).

**Authentication**: Required  
**Rate Limit Key**: `trips:collaborators:remove`

### Response

`204 No Content`

### Errors

- `400` - Invalid request (e.g., userId is not a UUID)
- `401` - Not authenticated
- `403` - You do not have permission to remove this collaborator
- `404` - Trip or collaborator not found
- `429` - Rate limit exceeded

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

#### cURL

```bash
curl -X GET "http://localhost:3000/api/trips/suggestions?limit=5&category=culture" \
  --cookie "sb-access-token=$JWT"
```

#### TypeScript/Fetch

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

#### Python/Requests

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
