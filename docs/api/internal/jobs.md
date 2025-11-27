# Background Jobs

Background job endpoints handled by Upstash QStash.

> **Access**: These endpoints use QStash signature verification and should only be called by the Upstash QStash service.

## Overview

Background jobs are used for:

- Asynchronous processing that doesn't need immediate response
- Long-running tasks that would timeout in a synchronous request
- Tasks that can be retried on failure

All job handlers are:

- **Idempotent**: Safe to retry without side effects
- **Stateless**: Don't rely on in-memory state
- **Verified**: Require valid QStash signatures

---

## `POST /api/jobs/notify-collaborators`

QStash job for notifying trip collaborators.

**Authentication**: QStash signature verification

### Request Body

Notification job data including:

| Field | Type | Description |
|-------|------|-------------|
| `tripId` | string | Trip ID |
| `event` | string | Event type |
| `collaboratorIds` | string[] | User IDs to notify |
| `message` | string | Notification message |

### Response

`200 OK`

### Errors

- `401` - Invalid QStash signature
- `500` - Notification delivery failed

### Retry Behavior

On failure, QStash will retry with exponential backoff:

- Max retries: 3
- Initial delay: 10 seconds
- Max delay: 5 minutes

---

## `POST /api/jobs/memory-sync`

Memory sync job for updating user memory indexes.

**Authentication**: QStash signature verification

### Request Body

Memory sync job data including:

| Field | Type | Description |
|-------|------|-------------|
| `userId` | string | User ID |
| `conversationId` | string | Conversation ID |
| `syncType` | string | Sync type (`full`, `incremental`) |

### Response

`200 OK`

### Errors

- `401` - Invalid QStash signature
- `500` - Memory sync failed

### Usage

This job is triggered after conversations to:

- Extract and index user preferences
- Update conversation summaries
- Maintain memory consistency

### Retry Behavior

On failure, QStash will retry with exponential backoff:

- Max retries: 3
- Initial delay: 30 seconds
- Max delay: 10 minutes
