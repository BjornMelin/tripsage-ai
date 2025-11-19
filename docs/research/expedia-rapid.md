# Expedia Rapid Integration Research

## Internal References

- `docs/prompts/tools/accommodation-details-tool-migration.md` (line 263) lists Expedia as an alternative accommodation detail provider beside Airbnb MCP and Booking.com; no dedicated ADR/SPEC currently defines an Expedia implementation.
- AGENTS.md + ADR-0020/0024/0026/0031/0036 and SPEC-001/010/015 still govern cross-cutting concerns (telemetry, cache/layout, BYOK, AI SDK v6), so a future Expedia ADR must inherit those constraints.

## External References

- Expedia Group Rapid developer hub: <https://developers.expediagroup.com/rapid> (entry point for Lodging Content, Shopping, Booking APIs, and SDKs).
- Rapid setup + launch requirements: <https://developers.expediagroup.com/rapid/setup> (covers partner onboarding, API key/secret issuance, sandbox vs production flow, B2B/B2C compliance checklists, Vrbo requirements, and optimization tips).
- Rapid Content API reference: <https://developers.expediagroup.com/rapid/lodging/content> (property metadata, descriptions, amenities, sustainability, pagination, guest reviews).
- Rapid Shopping API reference: <https://developers.expediagroup.com/rapid/lodging/shopping> (live availability, rate plans, payment types, test request catalog, filtering/options).
- Rapid Booking API reference: <https://developers.expediagroup.com/rapid/lodging/booking> (reservation workflow, guest/PII payload schema, confirmation/cancellation endpoints, error taxonomy).

## Open Questions / To-Do

1. Confirm Rapid authentication mode (current docs mention API key + shared secret → Basic/OAuth/HMAC). Need final spec + token caching strategy.
2. Determine caching strategy for Content API (Supabase tables vs Upstash). Identify data freshness SLAs.
3. Map payment + booking flow: Stripe charge first vs Rapid booking hold; align with ADR-0031 payment guardrails.
4. Capture rate-limit quotas + recommended retries for Shopping/Booking to size Upstash limits.
5. Draft ADR describing Expedia integration scope, architecture, and migration path from Airbnb MCP fallback.
