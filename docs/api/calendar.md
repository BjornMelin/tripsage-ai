# Calendar

Calendar events, status, and ICS import/export.

## `GET /api/calendar/status`

Get calendar sync status.

**Authentication**: Required  
**Rate Limit Key**: `calendar:status`

### Response

`200 OK`

```json
{
  "connected": true,
  "calendars": [
    {
      "id": "primary",
      "summary": "Primary Calendar",
      "timeZone": "America/New_York",
      "primary": true,
      "accessRole": "owner"
    }
  ]
}
```

### Errors

- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## `POST /api/calendar/freebusy`

Check calendar free/busy status.

**Authentication**: Required  
**Rate Limit Key**: `calendar:freebusy`

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `items` | array | Yes | Array of calendar items (min 1) - see schema below |
| `timeMin` | string/date | Yes | Start time (ISO 8601 or YYYY-MM-DD) |
| `timeMax` | string/date | Yes | End time (ISO 8601 or YYYY-MM-DD) |
| `timeZone` | string | No | Timezone (IANA timezone, default: UTC) |
| `calendarExpansionMax` | number | No | Maximum number of calendars to return when resolving calendar aliases into individual calendars. Default: 50, valid range: 1-1000. When limit is reached, results are truncated and a summary field indicates incomplete expansion. Example: requesting alias "<all-staff@company.com>" with max=5 returns first 5 individual calendars. |
| `groupExpansionMax` | number | No | Maximum number of groups to return when resolving group memberships into individual calendars. Default: 50, valid range: 1-1000. When limit is reached, results are truncated and a summary field indicates incomplete expansion. Example: requesting group "<team@company.com>" with max=10 returns first 10 member calendars. |

**Items Array Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Calendar ID |
| `attendees` | array | No | Array of attendees with `email` and optional `name` |

### Response

`200 OK`

**Response Structure:**

The `calendars` array maps 1:1 to the request `items` array in order. Each element in the response corresponds to the same-index item from the request. Items that couldn't be retrieved return an error object with an `error` field instead of `busy`/`available` arrays. No aggregation occurs across items - each calendar's availability is returned separately.

```json
{
  "calendars": [
    {
      "busy": [
        {
          "start": "2025-01-20T14:00:00Z",
          "end": "2025-01-20T15:00:00Z"
        }
      ],
      "available": [
        {
          "start": "2025-01-20T15:00:00Z",
          "end": "2025-01-20T16:00:00Z"
        }
      ]
    },
    {
      "error": "Calendar not found or access denied"
    }
  ]
}
```

### Errors

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## Events

### `GET /api/calendar/events`

List calendar events.

**Authentication**: Required  
**Rate Limit Key**: `calendar:events:read`

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `calendarId` | string | No | Calendar ID (default: "primary") |
| `timeMin` | string | No | Start time filter |
| `timeMax` | string | No | End time filter |
| `maxResults` | number | No | Maximum results (default: 250) |
| `pageToken` | string | No | Pagination token from previous response (use `nextPageToken` value) to retrieve next page of results |
| `orderBy` | string | No | Order by (`startTime`, `updated`) |
| `q` | string | No | Search query |
| `timeZone` | string | No | Timezone |
| `singleEvents` | boolean | No | Expand recurring events |
| `showDeleted` | boolean | No | Include deleted events |

#### Response

`200 OK`

```json
{
  "events": [
    {
      "id": "event-uuid-123",
      "summary": "Team Meeting",
      "description": "Quarterly planning session",
      "start": {
        "dateTime": "2025-01-20T14:00:00Z"
      },
      "end": {
        "dateTime": "2025-01-20T15:00:00Z"
      },
      "location": "Conference Room A",
      "attendees": [
        {
          "email": "user@example.com",
          "name": "John Doe",
          "responseStatus": "accepted"
        }
      ],
      "timeZone": "America/New_York"
    },
    {
      "id": "event-uuid-456",
      "summary": "Flight to NYC",
      "start": {
        "dateTime": "2025-01-21T10:00:00Z"
      },
      "end": {
        "dateTime": "2025-01-21T14:00:00Z"
      },
      "timeZone": "UTC"
    }
  ],
  "nextPageToken": "CiAKGjBpNDd2Nmp2Zml2cXRwYjBpOXA"
}
```

**Note**: `nextPageToken` is only included when more results are available. Use it as the `pageToken` query parameter in subsequent requests to retrieve the next page.

#### Errors

- `401` - Not authenticated
- `429` - Rate limit exceeded

---

### `POST /api/calendar/events`

Create a calendar event.

**Authentication**: Required  
**Rate Limit Key**: `calendar:events:create`

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `calendarId` | string | No | Calendar ID (default: "primary") |
| `summary` | string | Yes | Event title (max 1024 chars) |
| `start` | object | Yes | Start date/time |
| `end` | object | Yes | End date/time |
| `description` | string | No | Event description (max 8192 chars) |
| `location` | string | No | Location (max 1024 chars) |
| `attendees` | array | No | Attendee array |
| `reminders` | object | No | Reminders object |
| `recurrence` | array | No | Recurrence rules |
| `timeZone` | string | No | Timezone |
| `visibility` | string | No | Visibility level |
| `transparency` | string | No | Transparency (`opaque`, `transparent`) |

#### Response

`201 Created` - Returns created event

#### Errors

- `400` - Validation failed
- `401` - Not authenticated
- `429` - Rate limit exceeded

#### Example

```typescript
const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:3000";

// jwtToken is the JWT obtained from the authentication/login flow
// See docs/api/auth.md for details on obtaining the access token
const response = await fetch(`${BASE_URL}/api/calendar/events`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Cookie: `sb-access-token=${jwtToken}`,
  },
  body: JSON.stringify({
    summary: "Team Meeting",
    start: { dateTime: "2025-07-01T10:00:00Z" },
    end: { dateTime: "2025-07-01T11:00:00Z" },
    calendarId: "primary"
  }),
});
```

**Note**: Replace `BASE_URL` with your API endpoint. For local development use `http://localhost:3000`, for production use your deployed API URL.

---

### `PATCH /api/calendar/events`

Update a calendar event.

**Authentication**: Required  
**Rate Limit Key**: `calendar:events:update`

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `eventId` | string | Yes | Event ID |
| `calendarId` | string | No | Calendar ID (default: "primary") |

#### Request Body

Same fields as `POST /api/calendar/events`, all optional.

#### Response

`200 OK` - Returns updated event

#### Errors

- `400` - Validation failed
- `401` - Not authenticated
- `404` - Event not found
- `429` - Rate limit exceeded

---

### `DELETE /api/calendar/events`

Delete a calendar event.

**Authentication**: Required  
**Rate Limit Key**: `calendar:events:delete`

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `eventId` | string | Yes | Event ID |
| `calendarId` | string | No | Calendar ID (default: "primary") |

#### Response

`200 OK`

```json
{
  "success": true
}
```

#### Errors

- `401` - Not authenticated
- `404` - Event not found
- `429` - Rate limit exceeded

---

## ICS Import/Export

### `POST /api/calendar/ics/export`

Export calendar events to ICS format.

**Authentication**: Required  
**Rate Limit Key**: `calendar:ics:export`  
**Response**: `text/calendar` (ICS file)

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `calendarName` | string | No | Calendar name (default: "TripSage Calendar") |
| `events` | array | Yes | Array of calendar events (min 1) - see event schema below |
| `timezone` | string | No | Timezone |

**Event Schema (items in `events` array):**

| Field | Type | Required | Format/Description |
|-------|------|----------|-------------------|
| `start` | object | **Yes** | Start date/time. Supports both `date` (YYYY-MM-DD) and `dateTime` (ISO 8601) formats |
| `end` | object | **Yes** | End date/time. Supports both `date` (YYYY-MM-DD) and `dateTime` (ISO 8601) formats |
| `summary` | string | No | Event title/summary |
| `description` | string | No | Event description |
| `location` | string | No | Event location |
| `attendees` | array | No | Array of attendee objects with `email` and optional `name` |
| `uid` | string | No | Unique identifier for the event |
| `status` | string | No | Event status (e.g., `CONFIRMED`, `TENTATIVE`, `CANCELLED`) |
| `organizer` | object | No | Organizer object with `email` and optional `name` |
| `recurrence` | array | No | Recurrence rules (RRULE format) |

#### Response

`200 OK` - Returns ICS file with `Content-Disposition: attachment`

#### Errors

- `400` - Validation failed
- `401` - Not authenticated
- `429` - Rate limit exceeded

#### Example

```bash
# JWT is the access token returned from the authentication endpoint
# See docs/api/auth.md for details on obtaining the access token
JWT="your-access-token-here"  # Replace with your actual JWT token
BASE_URL="http://localhost:3000"  # Set to your API URL

# Minimal example with required fields only:
curl -X POST "${BASE_URL}/api/calendar/ics/export" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "start": {"dateTime": "2025-07-01T10:00:00Z"},
        "end": {"dateTime": "2025-07-01T14:00:00Z"}
      }
    ]
  }' \
  --output trip.ics

# Full example with optional fields:
curl -X POST "${BASE_URL}/api/calendar/ics/export" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "calendarName": "My Trip",
    "timezone": "America/New_York",
    "events": [
      {
        "summary": "Flight to NYC",
        "description": "Delta flight DL123",
        "location": "JFK Airport",
        "start": {"dateTime": "2025-07-01T10:00:00Z"},
        "end": {"dateTime": "2025-07-01T14:00:00Z"},
        "attendees": [
          {"email": "traveler@example.com", "name": "John Doe"}
        ],
        "status": "CONFIRMED"
      }
    ]
  }' \
  --output trip.ics
```

---

### `POST /api/calendar/ics/import`

Import calendar events from ICS format.

**Authentication**: Required  
**Rate Limit Key**: `calendar:ics:import`

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `icsData` | string | Yes | ICS file content |
| `validateOnly` | boolean | No | Validate only without importing (default: false). Set to true to validate ICS syntax without persisting events. |

#### Response

`200 OK`

```json
{
  "success": true,
  "imported": 3,
  "skipped": 0,
  "errors": [],
  "eventIds": ["event-uuid-1", "event-uuid-2", "event-uuid-3"]
}
```

#### Errors

- `400` - Invalid ICS data
- `401` - Not authenticated
- `429` - Rate limit exceeded
