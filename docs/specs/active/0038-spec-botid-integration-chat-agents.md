# SPEC-0038: BotID Integration for Chat and Agent Endpoints

## Overview

This specification defines the integration of Vercel BotID into TripSage AI's high-value API endpoints to protect against sophisticated automated bots while allowing legitimate AI assistants.

## Scope

### Protected Routes

| Route | Method | Rate Limit | Purpose |
|-------|--------|------------|---------|
| `/api/chat` | POST | 60/min | Non-streaming chat completions |
| `/api/chat/stream` | POST | 40/min | Streaming chat responses |
| `/api/agents/router` | POST | 100/min | Agent workflow classification |
| `/api/chat/attachments` | POST | 20/min | File upload handling |

### Out of Scope

- Public endpoints (landing pages, docs)
- Authentication endpoints (login, register)
- Webhook endpoints (server-to-server)
- Admin/internal endpoints

## API Behavior

### Bot Detection Response

When a bot is detected (and not a verified AI assistant):

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "error": "bot_detected",
  "reason": "Automated access is not allowed."
}
```

### Verified AI Assistants

The following verified bot categories are allowed through BotID protection:

- `ai_assistant` — ChatGPT, Perplexity, Claude web search, etc.

These requests are still subject to Upstash rate limiting.

**Logged events:**

```log
INFO  verified_ai_assistant_allowed { routeName, verifiedBotName, verifiedBotCategory }
```

### Blocked Bots

All other bots (including verified search crawlers, monitors, etc.) are blocked.

**Logged events:**

```log
WARN  bot_detected { routeName, isVerifiedBot, verifiedBotName, verifiedBotCategory }
```

## Implementation

### Client-Side Component

```tsx
// src/app/layout.tsx
import { BotIdClient } from "botid/react";

<BotIdClient
  routes={[
    "/api/chat",
    "/api/chat/stream",
    "/api/agents/router",
    "/api/chat/attachments",
  ]}
/>
```

**Requirements:**

- Must be rendered in the root layout
- Route list must exactly match server-side protected routes
- Runs invisible challenges on page sessions

### Server-Side Configuration

```typescript
// Route handler configuration
export const POST = withApiGuards({
  auth: true,
  botId: true,  // Enable BotID protection
  rateLimit: "chat:stream",
  telemetry: "chat.stream",
})(handler);
```

**Guard execution order:**

1. Create Supabase client
2. Check authentication (if enabled)
3. **Check BotID** (if enabled) ← New
4. Enforce rate limiting (if configured)
5. Validate schema (if provided)
6. Execute handler

### Helper Function

```typescript
// src/lib/security/botid.ts

/**
 * Asserts the current request is from a human (or verified AI assistant).
 *
 * @throws {BotDetectedError} If bot detected and not an allowed verified bot.
 */
export async function assertHumanOrThrow(
  routeName: string,
  options?: {
    level?: "basic" | "deep";
    allowVerifiedAiAssistants?: boolean;
  }
): Promise<void>;
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `botId` | `boolean \| "deep"` | `undefined` | Enable BotID. `true` for basic, `"deep"` for Kasada analysis |
| `level` | `"basic" \| "deep"` | `"basic"` | Detection level (deep costs $1/1000) |
| `allowVerifiedAiAssistants` | `boolean` | `true` | Allow AI assistants through |

## Local Development

BotID returns `isBot: false` in local development environments by default. This is expected behavior and cannot be changed without special configuration.

**Testing bot detection:**

- Unit tests: Mock `checkBotId()` via vitest mocks
- Integration tests: Test full flow with mocked responses
- Production testing: Use Vercel preview deployments

## Observability

### Logging

Logger namespace: `security.botid`

| Event | Level | Fields |
|-------|-------|--------|
| `verified_ai_assistant_allowed` | INFO | routeName, verifiedBotName, verifiedBotCategory |
| `bot_detected` | WARN | routeName, isVerifiedBot, verifiedBotName, verifiedBotCategory |

### Metrics

BotID metrics are available in:

- Vercel Dashboard → Project → Firewall → BotID
- Observability Plus (if enabled)

## Security Considerations

1. **Proxy rewrites**: Configured in `next.config.ts` to prevent ad-blocker interference
2. **No PII in logs**: Only route names and bot identifiers are logged
3. **Verified bot allowlist**: Limited to `ai_assistant` category only
4. **Rate limiting still applies**: Verified AI assistants are rate limited

## Dependencies

- `botid` package (v1.5.0+)
- Vercel deployment (BotID is Vercel-only)
- Next.js 15.3+ (for `<BotIdClient>` without config wrapper)

## Cost

| Mode | Plan | Price |
|------|------|-------|
| Basic | All Plans | Free |
| Deep Analysis | Pro/Enterprise | $1/1000 calls |

Current configuration uses **Basic mode only** (free).

## Related Documents

- ADR-0059: BotID Integration Decision
- ADR-0032: Centralized Rate Limiting
- [Vercel BotID Documentation](https://vercel.com/docs/botid)
