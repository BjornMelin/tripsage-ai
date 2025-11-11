# ADR-0020: AI SDK v6 Tool Registry and MCP Integration

**Date:** 2025-11-11
**Status:** Accepted
**Version:** 1.0.0
**Category:** frontend
**Domain:** AI SDK v6

## Context

- We are migrating from Python LangChain-style tools to a unified TypeScript tool registry using AI SDK v6 under `frontend/src/lib/tools/`.
- External APIs must be integrated via maintained clients or MCP where available (Airbnb via SSE/HTTP MCP, Duffel, Google Maps, OpenWeather, Firecrawl).

## Decision

- Implement a centralized tool registry `frontend/src/lib/tools/index.ts` and domain tools (`web-search`, `web-crawl`, `weather`, `flights`, `maps`, `accommodations`, `memory`).
- Integrate optional MCP tools discovery at runtime in `frontend/src/app/api/chat/stream/_handler.ts` using `@ai-sdk/mcp@1.0.0-beta.15` SSE transport.
- Enforce security via:
  - Upstash Redis caching and simple rate-limit compatible patterns.
  - Approval gating for sensitive operations (e.g., booking) in `frontend/src/lib/tools/approvals.ts`.
  - Timeouts and error mapping inside each tool’s execute function.

## Consequences

- Single implementation path on the frontend for tools; Python tool modules become obsolete and are candidates for deletion.
- Frontend gates (Biome, tsc, Vitest) validate the new implementation.
- Backend endpoints remain available for non-tool features until follow-up decommission.

## References

- Tool registry: `frontend/src/lib/tools/index.ts`
- Chat stream integration: `frontend/src/app/api/chat/stream/_handler.ts`
- MCP client: `@ai-sdk/mcp@1.0.0-beta.15`
