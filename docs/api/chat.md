# Chat

Chat sessions, messaging, and attachments.

## `POST /api/chat`

Non-streaming chat completion.

**Authentication**: Required (JWT via `sb-access-token` cookie or `Authorization: Bearer <token>` header)
**Rate Limit Key**: `chat:nonstream`

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `messages` | array | Yes | Array of chat messages |
| `sessionId` | string | No | Chat session ID |
| `model` | string | No | Model override |

### Response

`200 OK` - Returns complete chat response

```json
{
  "id": "chat-msg-123",
  "content": "This is the assistant's response",
  "role": "assistant",
  "tokens": {
    "input": 50,
    "output": 25
  }
}
```

### Errors

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

## `POST /api/chat/stream`

Streaming chat completion (SSE).

**Authentication**: Required (JWT via `sb-access-token` cookie or `Authorization: Bearer <token>` header)
**Rate Limit Key**: `chat:stream`
**Response**: `text/event-stream` (SSE)

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `messages` | array | Yes | Array of UI messages |
| `sessionId` | string | No | Chat session ID |
| `model` | string | No | Model override |
| `desiredMaxTokens` | number | No | Maximum tokens |

### Response

`200 OK` - SSE stream with chat messages

### Errors

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded

### Example

```bash
curl -N -X POST "http://localhost:3000/api/chat/stream" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```

---

## `POST /api/chat/send`

Send message to chat session.

**Authentication**: Required (JWT via `sb-access-token` cookie or `Authorization: Bearer <token>` header)
**Rate Limit Key**: `chat:nonstream`

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | Message content (max 10000 chars) |
| `conversationId` | string | No | Conversation ID |
| `attachments` | array | No | Attachment array |
| `context` | object | No | Context object |

### Response

`200 OK` - Returns chat response

### Errors

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded

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
    "title": "Trip Planning",
    "createdAt": "2025-01-15T10:00:00Z",
    "updatedAt": "2025-01-15T10:00:00Z"
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

`200 OK` - Returns messages array

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

`201 Created` - Returns created message

#### Errors

- `400` - Validation failed
- `401` - Not authenticated
- `404` - Session not found
- `429` - Rate limit exceeded

---

## Attachments

### `POST /api/chat/attachments`

Upload chat attachment (multipart form data).

**Authentication**: Required — derived from Supabase session cookie (`sb-access-token`). Caller-supplied `Authorization` headers are ignored for this endpoint.
**Rate Limit Key**: `chat:attachments`

#### Request

Multipart form data with file uploads.

**Form Field Names:**

- Single file: `file`
- Multiple files: `files` (can include multiple files with same field name)

**File Constraints:**

- **Maximum file size**: 10 MB (10,485,760 bytes)
- **Maximum files per request**: 5 files
- **Maximum total payload (Content-Length)**: 50 MB — requests advertising a larger body are rejected with `413`
- **Accepted MIME types**: All types accepted (validation performed by backend)
- **Multiple files**: Supported - submit up to 5 files in a single request

**Content-Type**: `multipart/form-data`

#### Response

`200 OK` - Returns attachment metadata

```json
{
  "files": [
    {
      "id": "file-uuid-abc123",
      "name": "travel-document.pdf",
      "type": "application/pdf",
      "size": 524288,
      "status": "completed",
      "url": "/api/attachments/file-uuid-abc123/download"
    },
    {
      "id": "file-uuid-def456",
      "name": "boarding-pass.png",
      "type": "image/png",
      "size": 245760,
      "status": "completed",
      "url": "/api/attachments/file-uuid-def456/download"
    }
  ],
  "urls": [
    "/api/attachments/file-uuid-abc123/download",
    "/api/attachments/file-uuid-def456/download"
  ]
}
```

#### Errors

- `400` - Invalid request:
  - No files uploaded
  - File size exceeds 10 MB limit
  - More than 5 files submitted
  - Invalid content type (not multipart/form-data)
- `401` - Not authenticated
- `429` - Rate limit exceeded
- `502` - Backend upload service error
