# ADR-0023: Adopt AI SDK v6 Foundations (Next.js App Router)

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-01
**Category**: frontend
**Domain**: AI SDK / Next.js App Router

## Context

- We are migrating chat and related AI features to a library-first foundation in the Next.js frontend. The goals are: streaming primitives, low custom code, and clean server-only secret handling.
- Official docs and examples (AI SDK v6) recommend `streamText` and `toUIMessageStreamResponse()` for server routes; AI Elements provides composable chat UI primitives.

## Decision

- Adopt Vercel AI SDK v6 patterns with a demo streaming route and minimal AI Elements UI, keeping secrets server-only and avoiding bespoke streaming code.
- Implement a demo route at `src/app/api/_health/stream/route.ts` returning a UI Message Stream response.
- Add AI Elements components (`conversation`, `message`, `prompt-input`) via the CLI and compose a placeholder page at `src/app/ai-demo/page.tsx`.

## Options Considered

1. Custom streaming (ReadableStream/SSE) + bespoke chat components
2. AI SDK v6 (`streamText`) + AI Elements (shadcn-based) [Chosen]
3. Alternate SDKs or previous AI SDK v5 patterns

## Rationale (Decision Framework)

- Solution Leverage (35%): 9.5 → 3.325
- Application Value (30%): 9.2 → 2.76
- Maint. Load (25%): 9.4 → 2.35
- Adaptability (10%): 8.8 → 0.88
- Weighted Total: 9.315 / 10 (≥ 9.0 threshold)

## Security Notes

- Route is server-only and streams over a typed UI message protocol; no secrets are included in responses.
- Supabase admin usage remains server-only. Client code never imports server factories. Environment variables for admin keys must stay out of client bundles.

## Consequences

- Faster feature iteration with minimal custom infrastructure.
- Reduced maintenance surface for streaming and chat UI.
- Clear path to expand with tool-calling and provider management.

## References

- AI SDK v6 Docs: Generating Text, Streaming, Next.js App Router, AI Elements
- Research logs: exa.crawling_exa outputs for target pages; zen.consensus scoring
