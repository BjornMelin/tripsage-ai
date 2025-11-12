# ADR-0038: Frontend Hybrid Agents for Destination Research & Itineraries

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2025-11-12  
**Category**: Architecture  
**Domain**: AI Orchestration / Frontend  
**Related ADRs**: ADR-0026, ADR-0028, ADR-0031, ADR-0036  
**Related Specs**: SPEC-0019

## Context

- The legacy destination research and itinerary agents lived inside `tripsage/` (FastAPI + LangGraph). Those nodes depended on Python MCP tools, creating drift from the new AI SDK v6-first frontend stack and blocking our Next.js-only deployments.
- We have already adopted AI SDK v6, AI Elements chat primitives, BYOK provider registry, Supabase SSR, and Upstash rate limiting on the frontend. However, destination-specific tooling never migrated, causing the regression highlighted in the review (missing `webcrawl_search`).
- We now require all agentic orchestration to happen inside Next.js Route Handlers, using Vercel AI SDK v6 ToolLoopAgent, Supabase auth, Upstash caching, and shared TypeScript tool definitions. The frontend must fully reproduce destination research & itinerary outputs without reaching back into `tripsage/` or `tripsage_core/`.

## Decision

We will replace the Python-based destination research and itinerary agents with **hybrid ToolLoopAgent workflows implemented entirely in `frontend/`**:

1. **Next.js Route Handlers** under `src/app/api/agents/destinations` and `.../itineraries` will host ToolLoopAgent instances bound to our TypeScript tool registry. The handlers stream UI messages via `toUIMessageStreamResponse()`.
2. **Hybrid Guardrails**: each tool invocation passes through deterministic validators (Zod schemas, Upstash rate limits, cache lookups). The ToolLoop is capped via `stopWhen` conditions and summarized deterministically before responding.
3. **Shared Schemas & Prompts**: destination + itinerary request/response schemas, prompt templates, and telemetry contracts are centralized in `frontend/src/schemas` and `frontend/src/prompts` for reuse by UI, tests, and observability.
4. **AI Elements-first UX**: chat quick actions, structured cards, and timelines render the new agent outputs without dumping JSON, reusing the existing AI Elements Conversation/PromptInput components.
5. **Telemetry & Rollout**: tool-level metrics (cache hits, validator rejections, budgets) flow through the existing telemetry stack; feature flags gate rollout until parity is confirmed.

## Consequences

### Positive

- Removes backend-on-frontend dependency: frontend owns research + itinerary logic with consistent TypeScript tooling.
- Unlocks richer UX (cards, timelines, sources) without cross-stack serialization hurdles.
- Hybrid guardrails provide reliability comparable to deterministic flows while leveraging AI SDK tool orchestration.
- Simplifies deployment by keeping all agent changes within a single Next.js project.

### Negative

- Increases complexity inside `frontend/` (ToolLoop orchestration, caching, telemetry) and requires careful testing to avoid regressions.
- Requires new Supabase tables/records for destination research persistence if we choose to store summaries.
- Demands additional monitoring to ensure hybrid loops do not exceed budgets or silently fail.

### Neutral

- Backend codebase shrinks; however, teams maintaining legacy Python tooling must archive historical context separately.
- Tool schemas now reside in TypeScript; Python consumers (if any) must be updated or deprecated.

## Alternatives Considered

### A. Pure ToolLoopAgent Runtime

- Pros: minimum scaffolding, maximum AI flexibility.  
- Cons: unpredictable execution, hard to test and monitor, regressed reliability vs. backend baseline. Rejected in consensus scoring (5.75/10) due to low maintenance and adaptability scores.

### B. Fully Deterministic Workflows

- Pros: simple to test, no AI autonomy.  
- Cons: requires re-implementing complex research flows manually, offers little leverage from AI SDK features, limited adaptability (4.83/10). Rejected because it would still involve high maintenance while underutilizing the AI stack.

### C. Hybrid ToolLoop + Guardrails (Chosen)

- Balances flexibility and control, achieved the required ≥9/10 consensus score (9.20) and aligns with AI SDK v6 design guidance.

## References

- SPEC-0019 (Hybrid Destination & Itinerary Agents).  
- AI SDK v6 Agents documentation (ToolLoopAgent, tool schemas).  
- Next.js route handler docs for streaming responses.
