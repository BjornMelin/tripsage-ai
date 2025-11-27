# Settings & Miscellaneous

User settings, embeddings, flights utility, and telemetry endpoints.

## User Settings

### `GET /api/user-settings`

Get user settings.

**Authentication**: Required  
**Rate Limit Key**: `user-settings:get`

#### Response

`200 OK` - Returns user settings

#### Errors

- `401` - Not authenticated
- `429` - Rate limit exceeded

---

### `POST /api/user-settings`

Update user settings.

**Authentication**: Required  
**Rate Limit Key**: `user-settings:update`

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `theme` | string | No | UI theme preference (`light`, `dark`, `auto`) |
| `language` | string | No | Language preference (ISO 639-1 code) |
| `timezone` | string | No | Timezone (IANA timezone identifier) |
| `notifications` | object | No | Notification settings {email: boolean, push: boolean, inApp: boolean} |
| `privacy` | object | No | Privacy settings {profileVisible: boolean, shareActivity: boolean} |
| `preferences` | object | No | Custom preferences (key-value pairs) |

#### Response

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

#### Errors

- `400` - Validation failed
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## Embeddings

### `POST /api/embeddings`

Generate embeddings.

**Authentication**: Required  
**Rate Limit Key**: `embeddings`

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Text to embed |
| `model` | string | No | Embedding model |

#### Response

`200 OK` - Returns embedding vector

#### Errors

- `400` - Invalid request
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## Flights Utility

### `GET /api/flights/popular-destinations`

Get popular flight destinations.

**Authentication**: Required  
**Rate Limit Key**: `flights:popular-destinations`

#### Response

`200 OK` - Returns popular destinations list

#### Errors

- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## Files & Attachments

### `GET /api/attachments/files`

List user files.

**Authentication**: Required  
**Rate Limit Key**: `attachments:files`

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | number | No | Maximum results to return (default: 20, max: 100) |
| `offset` | number | No | Number of results to skip for pagination (default: 0) |
| `type` | string | No | Filter by file type (e.g., "image", "document", "pdf", "video") |
| `sort` | string | No | Sort order (`name`, `date`, `size`, default: `date`) |
| `order` | string | No | Sort direction (`asc`, `desc`, default: `desc`) |

#### Response

`200 OK` - Returns files list

#### Errors

- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## Telemetry Demo

### `POST /api/telemetry/ai-demo`

Demo/observability endpoint for telemetry.

**Authentication**: Required  
**Rate Limit Key**: `telemetry:ai-demo`

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `modelName` | string | Yes | AI model to use for demo (e.g., "gpt-4", "claude-3-opus") |
| `prompt` | string | Yes | Input prompt for the AI model |
| `temperature` | number | No | Temperature for sampling (0-2, default: 1) |
| `maxTokens` | number | No | Maximum response tokens (default: 256) |
| `userId` | string | No | User ID for telemetry tracking |
| `sessionId` | string | No | Session ID for tracking related requests |
| `metadata` | object | No | Additional metadata for observability |

#### Response

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

#### Errors

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded
