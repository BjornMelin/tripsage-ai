# Chat

Chat sessions, messaging, and attachments.

## `POST /api/chat`

Streaming chat completion using the AI SDK v6 **UI message stream protocol**.

**Authentication**: Required (JWT via `sb-access-token` cookie or `Authorization: Bearer <token>` header)
**Rate Limit Key**: `chat:stream`
**Response**: `text/event-stream` (AI SDK UI message stream protocol; header `x-vercel-ai-ui-message-stream: v1`)

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `messages` | array | Yes | Array of AI SDK `UIMessage` objects |
| `sessionId` | string | No | Chat session ID |
| `model` | string | No | Model override |
| `desiredMaxTokens` | number | No | Maximum output tokens |

### Response

`200 OK` - Streams an AI SDK UI message stream. The server also returns:

- header `x-tripsage-session-id` (resolved/created session id)
- assistant message metadata includes `sessionId` on the `start` part

### Errors

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded

### Example

```bash
curl -N -X POST "http://localhost:3000/api/chat" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "id": "msg-1",
        "role": "user",
        "parts": [{ "type": "text", "text": "Hello" }]
      }
    ]
  }'
```

---

## Sessions

### `GET /api/chat/sessions`

List chat sessions for authenticated user.

**Authentication**: Required (JWT via `sb-access-token` cookie or `Authorization: Bearer <token>` header)
**Rate Limit Key**: `chat:sessions:list`

#### Response

`200 OK`

```json
[
  {
    "id": "session-uuid",
    "created_at": "2025-01-15T10:00:00Z",
    "updated_at": "2025-01-15T10:00:00Z",
    "metadata": { "title": "Trip Planning" }
  }
]
```

#### Errors

- `401` - Not authenticated
- `429` - Rate limit exceeded

---

### `POST /api/chat/sessions`

Create a new chat session.

**Authentication**: Required (JWT via `sb-access-token` cookie or `Authorization: Bearer <token>` header)
**Rate Limit Key**: `chat:sessions:create`

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | No | Session title |

#### Response

`201 Created` - Returns created session

```json
{ "id": "session-uuid" }
```

#### Errors

- `400` - Validation failed
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

### `GET /api/chat/sessions/{id}`

Get a specific chat session.

**Authentication**: Required  
**Rate Limit Key**: `chat:sessions:get`

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Session ID |

#### Response

`200 OK` - Returns session object

#### Errors

- `401` - Not authenticated
- `404` - Session not found
- `429` - Rate limit exceeded

---

### `DELETE /api/chat/sessions/{id}`

Delete a chat session.

**Authentication**: Required  
**Rate Limit Key**: `chat:sessions:delete`

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Session ID |

#### Response

`204 No Content`

#### Errors

- `401` - Not authenticated
- `404` - Session not found
- `429` - Rate limit exceeded

---

## Messages

### `GET /api/chat/sessions/{id}/messages`

List messages in a chat session.

**Authentication**: Required  
**Rate Limit Key**: `chat:sessions:messages:list`

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Session ID |

#### Response

`200 OK` - Returns an array of AI SDK `UIMessage` objects (including tool invocation parts where available).

#### Errors

- `401` - Not authenticated
- `404` - Session not found
- `429` - Rate limit exceeded

---

### `POST /api/chat/sessions/{id}/messages`

Create a message in a chat session.

**Authentication**: Required  
**Rate Limit Key**: `chat:sessions:messages:create`

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Session ID |

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | Yes | Message content |
| `role` | string | Yes | Message role (`user`, `assistant`, `system`) |

#### Response

`201 Created` - No body

#### Errors

- `400` - Validation failed
- `401` - Not authenticated
- `404` - Session not found
- `429` - Rate limit exceeded

---

## Attachments

### `POST /api/chat/attachments`

Create signed upload URLs (Supabase Storage) + persist attachment metadata.

**Authentication**: Required (JWT via `sb-access-token` cookie or `Authorization: Bearer <token>` header)
**Rate Limit Key**: `chat:attachments`

#### Request

JSON body describing the files to be uploaded. The server returns signed upload URLs and tokens.
The client uploads directly to Supabase Storage using `uploadToSignedUrl`.

At least one of `chatId` or `tripId` is required. `chatMessageId` is optional but requires `chatId`.
If both `chatId` and `tripId` are provided, the attachment is associated with both.

Chat-scoped example:

```json
{
  "chatId": "uuid",
  "chatMessageId": 123,
  "files": [
    { "originalName": "a.pdf", "mimeType": "application/pdf", "size": 12345 }
  ]
}
```

Trip-scoped example:

```json
{
  "tripId": 42,
  "files": [
    { "originalName": "a.pdf", "mimeType": "application/pdf", "size": 12345 }
  ]
}
```

#### Response

`200 OK` - Returns signed upload details.

```json
{
  "uploads": [
    {
      "attachmentId": "file-uuid-abc123",
      "mimeType": "application/pdf",
      "originalName": "a.pdf",
      "path": "userId/chatId/file-uuid-abc123/a.pdf",
      "signedUrl": "https://...",
      "size": 12345,
      "token": "token-from-supabase"
    }
  ]
}
```

#### Errors

- `400` - Invalid request:
  - Missing `chatId`/`tripId`
  - File size/type/count constraints
- `401` - Not authenticated
- `429` - Rate limit exceeded
- `500` - Failed to create signed upload URLs
