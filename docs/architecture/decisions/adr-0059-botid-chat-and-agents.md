# ADR-0059: BotID Integration for Chat and Agent Endpoints

**Status**: Accepted

## Context

High-value API endpoints in TripSage AI are common targets for sophisticated automated bots:

- `/api/chat` — Streaming chat responses
- `/api/agents/router` — Agent workflow classification
- `/api/chat/attachments` — Attachment signed upload URL issuance

Current protection relies solely on Upstash rate limiting, which is effective for volumetric control but does not distinguish between human users and sophisticated bots that mimic real browser behavior.

Sophisticated bots can:

- Run JavaScript and solve CAPTCHAs
- Use tools like Playwright/Puppeteer to simulate human interactions
- Blend in with normal traffic patterns
- Bypass traditional rate limiting by distributing requests

## Decision

Integrate Vercel BotID into the four high-value routes, combining it with existing Upstash rate limiting:

1. **BotID** handles per-request bot classification (human vs. bot detection)
2. **Upstash rate limiting** handles volumetric control (requests per minute)

Guard execution order in `withApiGuards`:

```text
Request → Auth Check → BotID Check → Rate Limit → Schema Validation → Handler
```

BotID runs after auth (need user context for logging) but before rate limiting (bot traffic shouldn't count against user limits).

### Configuration

- **Mode**: Basic (free tier) — validates browser sessions
- **Verified AI assistants**: Allowed by default for chat/agent routes (ChatGPT, Perplexity, Claude web search, etc.)
- **Non-AI bots**: Blocked (search crawlers, monitors, scrapers)

### Response on Bot Detection

```json
HTTP 403 Forbidden
Content-Type: application/json

{
  "error": "bot_detected",
  "reason": "Automated access is not allowed."
}
```

## Rationale (Decision Framework)

- **Leverage (35%)**: 9.0 — Uses Vercel's managed BotID service with Kasada-powered detection
- **Value (30%)**: 9.2 — Protects expensive AI compute from abuse while allowing legitimate AI assistants
- **Maintenance (25%)**: 8.8 — Single configuration point in `withApiGuards` factory
- **Adaptability (10%)**: 9.0 — Can upgrade to Deep Analysis mode per-route if needed
- **Weighted total**: 9.03/10 (≥ 9.0 threshold)

## Consequences

### Positive

- Sophisticated bot traffic blocked before consuming AI resources
- Verified AI assistants (ChatGPT, Perplexity, etc.) can still access APIs
- Centralized in `withApiGuards` — easy to enable for new routes
- No cost for basic mode
- Fire-and-forget logging for security monitoring

### Negative

- Requires Vercel deployment (BotID is Vercel-only)
- Local development always returns `isBot: false` (cannot test detection locally)
- Deep Analysis mode costs $1/1000 calls if enabled
- Requires client-side BotID initialization (`initBotId`) to provide browser signals for server checks

### Neutral

- Bot traffic no longer counts against rate limits (by design)
- Verified bot allowlist limited to `ai_assistant` category

## Implementation

Key files:

- `src/lib/security/botid.ts` — `assertHumanOrThrow()` helper and `BotDetectedError`
- `src/lib/api/factory.ts` — `GuardsConfig.botId` option
- `src/instrumentation-client.ts` — `initBotId({ protect })` client init
- `src/config/botid-protect.ts` — Canonical `protect` rules for BotID client init
- `next.config.ts` — `withBotId(nextConfig)` wrapper to enable BotID rewrites

## References

- [Vercel BotID Documentation](https://vercel.com/docs/botid)
- [BotID Get Started Guide](https://vercel.com/docs/botid/get-started)
- [Verified Bots Directory](https://vercel.com/docs/botid/verified-bots)
- [bots.fyi](https://bots.fyi) — Vercel's verified bot directory
- ADR-0032: Centralized Rate Limiting
- SPEC-0038: BotID Integration Specification (archived; superseded by SPEC-0108)
