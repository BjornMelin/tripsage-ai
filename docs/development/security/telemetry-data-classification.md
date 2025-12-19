# Telemetry Data Classification (server + client)

This document defines what TripSage is allowed to emit into telemetry spans, span events, and structured logs produced via `@/lib/telemetry/*`.

## Goals

- Prevent secrets/PII from reaching telemetry backends.
- Keep attributes low-cardinality to avoid cost explosions and unusable dashboards.
- Enable correlation without exposing raw identifiers.

## Data classes

### Disallowed (never emit)

- Secrets: API keys, tokens, signing keys, `Authorization` headers, cookies, webhook signatures, JWTs, service-role keys.
- Raw PII: email, name, address, phone, payment details.
- Raw identifiers that can be joined to user records:
  - `user.id`, `session.id`, `conversation.id`, `trip.id` when it is user-specific and could be used for enumeration.
- Full request bodies or raw prompts/messages.

### Allowed (safe by default)

- Low-cardinality metadata:
  - Route/method names (prefer stable route keys/templates; avoid raw request paths that include IDs), feature flags, boolean switches, error codes, retry counts.
  - Provider model IDs (e.g., `gpt-4o`) and tool names.
- Aggregations and sizes:
  - Token counts, character counts, byte sizes, durations (ms), item counts.
- Hashed identifiers (pseudonyms):
  - `*.id_hash` produced via HMAC-SHA256 with a server-side secret.

### Allowed with caution (review required)

- Partial error messages: only when redacted and not user-controlled.
- User-generated content samples: generally avoid; if required for debugging, prefer truncation + explicit approval and ensure it does not contain PII.
- Operational alert attributes: never include raw user-provided strings; prefer booleans + lengths, and (if correlation is required) a short one-way hash fingerprint.

## Identifier policy (required)

Do not emit raw user/session identifiers in telemetry by default.

- Use `hashTelemetryIdentifier()` from `src/lib/telemetry/identifiers.ts`:
  - Output attribute keys: `user.id_hash`, `session.id_hash` (or similar `*.id_hash`).
  - Input: raw identifier string.
  - Hash: `HMAC-SHA256(identifier, TELEMETRY_HASH_SECRET)` (stable pseudonym).
- In production, `TELEMETRY_HASH_SECRET` must be configured. In non-production, if it is unset, do not emit identifier attributes at all (fail-safe).

## Logging policy (required)

- Server modules should not use `console.*` (use `createServerLogger()` or telemetry events).
- Never log raw signature headers (e.g., QStash `Upstash-Signature`). If correlation is required, log a short hash prefix only.

## Review checklist

Before adding new telemetry attributes/events:

- [ ] No secrets/PII/raw IDs are included.
- [ ] Attributes are low-cardinality (no unbounded user input).
- [ ] Any identifiers are emitted as `*.id_hash` only, guarded by `TELEMETRY_HASH_SECRET` (required in production).
- [ ] Any user-provided strings are truncated and justified.
- [ ] If an operational alert is emitted, it is gated/deduped to prevent spam.
