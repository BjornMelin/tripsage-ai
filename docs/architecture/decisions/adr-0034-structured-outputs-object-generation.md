# ADR: Structured Outputs & Object Generation (AI SDK v6)

Status: Accepted

Context

- Responses that feed UI or downstream services benefit from schema validation. AI SDK v6 provides structured output (`streamObject`/`object` helpers) and AI SDK UI object support.

Decision

- Use AI SDK v6 structured outputs for server responses that map to typed objects (e.g., itinerary segments, booking quotes). Define Zod schemas and validate server-side.
- UI object rendering is optional; keep KISS by returning JSON to the client unless UI needs streaming object rendering.

Rationale (Decision Framework)

- Leverage (35%): 9.2 — native library features.
- Value (30%): 9.0 — safer integrations; fewer parsing bugs.
- Maint. (25%): 9.1 — typed contracts reduce drift.
- Adapt (10%): 8.7 — schemas evolve with versions.
- Weighted total: 9.15/10.

Consequences

- Introduce shared `schemas/` with ownership in frontend for AI outputs.
- Add tests to validate schema conformance and error mapping.

References

- Generating Structured Data: <https://v6.ai-sdk.dev/docs/ai-sdk-core/generating-structured-data>
- AI SDK UI Object Generation: <https://ai-sdk.dev/docs/ai-sdk-ui/object-generation>
