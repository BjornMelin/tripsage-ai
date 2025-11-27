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
| `calendarExpansionMax` | number | No | Calendar expansion max (default: 50) |
| `groupExpansionMax` | number | No | Group expansion max (default: 50) |

**Items Array Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Calendar ID |
| `attendees` | array | No | Array of attendees with `email` and optional `name` |

### Response

`200 OK`

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

`200 OK` - Returns events list

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
| `events` | array | Yes | Array of calendar events (min 1) |
| `timezone` | string | No | Timezone |

#### Response

`200 OK` - Returns ICS file with `Content-Disposition: attachment`

#### Errors

- `400` - Validation failed
- `401` - Not authenticated
- `429` - Rate limit exceeded

#### Example

```bash
BASE_URL="http://localhost:3000"  # Set to your API URL
curl -X POST "${BASE_URL}/api/calendar/ics/export" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "calendarName": "My Trip",
    "events": [
      {
        "summary": "Flight",
        "start": {"dateTime": "2025-07-01T10:00:00Z"},
        "end": {"dateTime": "2025-07-01T14:00:00Z"}
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
