# Settings & Miscellaneous

User settings, embeddings, flights utility, and telemetry endpoints.

## User Settings

### `GET /api/user-settings`

Get user settings.

**Authentication**: Required  
**Rate Limit Key**: `user-settings:get`

#### Response (GET /api/user-settings)

`200 OK` - Returns user settings

#### Errors (GET /api/user-settings)

- `401` - Not authenticated
- `429` - Rate limit exceeded

---

### `POST /api/user-settings`

Update user settings.

**Authentication**: Required  
**Rate Limit Key**: `user-settings:update`

#### Request Body (POST /api/user-settings)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `theme` | string | No | UI theme preference (`light`, `dark`, `auto`) |
| `language` | string | No | Language preference (ISO 639-1 code) |
| `timezone` | string | No | Timezone (IANA timezone identifier) |
| `notifications` | object | No | Notification settings {email, push, inApp} |
| `privacy` | object | No | Privacy settings {profileVisible, shareActivity} |
| `preferences` | object | No | Custom preferences (key-value pairs) |

#### Response (POST /api/user-settings)

`200 OK`

```json
{
  "theme": "dark",
  "language": "en",
  "timezone": "America/New_York",
  "notifications": {
    "email": true,
    "push": false,
    "inApp": true
  },
  "privacy": {
    "profileVisible": false,
    "shareActivity": false
  },
  "updatedAt": "2025-01-20T15:30:00Z"
}
```

Returns all settings fields with current values.

#### Errors (POST /api/user-settings)

- `400` - Validation failed
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## Embeddings

### `POST /api/embeddings`

Generate embeddings.

**Authentication**: Required  
**Rate Limit Key**: `embeddings`

#### Request Body (POST /api/embeddings)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Text to embed |
| `model` | string | No | Embedding model |

#### Response (POST /api/embeddings)

`200 OK` - Returns embedding vector

```json
{
  "embedding": [0.0234, -0.0156, 0.0423, -0.0089, 0.0312, 0.0178],
  "modelId": "text-embedding-3-small",
  "success": true,
  "usage": {
    "promptTokens": 12,
    "totalTokens": 12
  },
  "id": "property-123",
  "persisted": true
}
```

The `embedding` array continues to 1536 numeric values.

#### Errors (POST /api/embeddings)

- `400` - Invalid request
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## Flights Utility

### `GET /api/flights/popular-destinations`

Get popular flight destinations.

**Authentication**: Required  
**Rate Limit Key**: `flights:popular-destinations`

#### Response (GET /api/flights/popular-destinations)

`200 OK` - Returns popular destinations list

```json
[
  {
    "code": "NYC",
    "name": "New York",
    "country": "USA",
    "savings": "$127"
  },
  {
    "code": "LAX",
    "name": "Los Angeles",
    "country": "USA",
    "savings": "$89"
  },
  {
    "code": "LHR",
    "name": "London",
    "country": "UK",
    "savings": "$234"
  }
]
```

#### Errors (GET /api/flights/popular-destinations)

- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## Files & Attachments

### `GET /api/attachments/files`

List user files.

**Authentication**: Required — derived from Supabase session cookie (`sb-access-token`). Caller-supplied `Authorization` headers are ignored for this endpoint.  
**Rate Limit Key**: `attachments:files`

#### Query Parameters (GET /api/attachments/files)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | number | No | Max results (default: 20, max: 100) |
| `offset` | number | No | Results to skip (default: 0) |
| `type` | string | No | File type filter (e.g., "image", "pdf", "video") |
| `sort` | string | No | Sort order (`name`, `date`, `size`, default: `date`) |
| `order` | string | No | Sort direction (`asc`, `desc`, default: `desc`) |

#### Response (GET /api/attachments/files)

`200 OK` - Returns files list

```json
{
  "files": [
    {
      "id": "file-uuid-1",
      "filename": "vacation-itinerary.pdf",
      "type": "application/pdf",
      "size": 245760,
      "uploadedAt": "2025-01-20T10:30:00Z"
    },
    {
      "id": "file-uuid-2",
      "filename": "hotel-confirmation.png",
      "type": "image/png",
      "size": 524288,
      "uploadedAt": "2025-01-20T11:45:00Z"
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

#### Errors (GET /api/attachments/files)

- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## Telemetry Demo

### `POST /api/telemetry/ai-demo`

Demo/observability endpoint for telemetry.

**Authentication**: Required  
**Rate Limit Key**: `telemetry:ai-demo`

#### Request Body (POST /api/telemetry/ai-demo)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `modelName` | string | Yes | AI model (e.g., "gpt-4", "claude-3-opus") |
| `prompt` | string | Yes | Input prompt for the AI model |
| `temperature` | number | No | Temperature for sampling (0-2, default: 1) |
| `maxTokens` | number | No | Maximum response tokens (default: 256) |
| `userId` | string | No | User ID for telemetry tracking |
| `sessionId` | string | No | Session ID for tracking related requests |
| `metadata` | object | No | Additional metadata for observability |

#### Response (POST /api/telemetry/ai-demo)

`200 OK`

```json
{
  "id": "demo-request-uuid",
  "model": "gpt-4",
  "response": "The AI model response text here...",
  "tokensUsed": {
    "prompt": 15,
    "completion": 42,
    "total": 57
  },
  "processingTime": 325,
  "timestamp": "2025-01-20T15:30:00Z"
}
```

#### Errors (POST /api/telemetry/ai-demo)

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## Activity Booking Telemetry

### `POST /api/telemetry/activities`

Captures client-side booking interactions (e.g., URL resolution and fallbacks).

**Authentication**: Not required  
**Rate Limit Key**: `telemetry:post`

#### Request Body (POST /api/telemetry/activities)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `eventName` | string | Yes | Regex: `/^[a-z][a-z0-9._]{0,99}$/i` |
| `attributes` | object | No | Up to 25 entries (string/number/boolean) |
| `level` | string | No | One of `info`, `warning`, `error` (default: `info`) |

#### Response (POST /api/telemetry/activities)

`200 OK` on success.

#### Errors (POST /api/telemetry/activities)

- `400` - Invalid event name or attributes
- `429` - Rate limit exceeded
