# Internal API

Internal endpoints for admin operations and system integrations. These endpoints are not intended for end-user consumption.

## Overview

Internal endpoints fall into three categories:

| Category | Description | Authentication |
|----------|-------------|----------------|
| [Agent Config](config.md) | Agent configuration management | Admin user |
| [Webhooks](webhooks.md) | Database and file event handlers | Webhook signature |
| [Jobs](jobs.md) | Background job handlers | QStash signature |

## Access Control

### Admin Endpoints

Agent configuration endpoints require admin-level authentication:

- User must be authenticated via Supabase SSR cookies
- User must have admin role in the system

### Webhook Endpoints

Webhook endpoints verify signatures to ensure requests originate from trusted sources:

- Supabase webhooks use the `SUPABASE_WEBHOOK_SECRET`
- Requests without valid signatures are rejected with `401 Unauthorized`

### Job Endpoints

Background job endpoints are called by Upstash QStash:

- Requests are verified using QStash signature verification
- Jobs run asynchronously and should be idempotent
- Invalid signatures result in `401 Unauthorized`

## Security Notes

- Never expose internal endpoints to untrusted clients
- Webhook and job endpoints should only be called by their respective services
- Admin endpoints should only be accessible to authorized administrators
- All internal endpoints are rate-limited to prevent abuse
