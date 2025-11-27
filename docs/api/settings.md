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

User settings object (partial update supported).

#### Response

`200 OK` - Returns updated settings

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

Query parameters are passed through to the backend.

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

Demo parameters.

#### Response

`200 OK` - Returns demo result

#### Errors

- `401` - Not authenticated
- `429` - Rate limit exceeded
