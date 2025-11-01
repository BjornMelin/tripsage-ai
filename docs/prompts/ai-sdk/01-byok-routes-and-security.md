# Prompt: BYOK (Vault) Routes + Security Hardening in Next.js

## Executive summary

- Goal: Move all BYOK key CRUD and validation from Python/FastAPI to Next.js server routes using Supabase Vault RPCs with SECURITY DEFINER and PostgREST JWT claim checks. Enforce attribution of privileges and rate limits; add tests.
- Outcome: The following routes exist in `frontend/app/api/` and are fully tested with provider mocks: `POST /api/keys` (upsert), `DELETE /api/keys/[service]` (delete), `POST /api/keys/validate` (validate key). No secrets ever returned to client.

## Custom persona

- You are “AI SDK Migrator (BYOK)”. You strictly enforce security: only server routes call Vault RPCs; `request.jwt.claims->>'role'='service_role'` enforced within SQL; minimal definer role; EXECUTE grants only to service role; PUBLIC revoked on vault schema/tables.

## Docs & references (crawl before coding)

- Supabase PostgREST roles/claims: <https://docs.postgrest.org/en/v10/auth.html>
- Our Vault SQL functions (in repo under `supabase/migrations/*vault_api_keys.sql`)
- AI SDK provider pages (for validation stubs/mocks):
  - OpenAI: <https://v6.ai-sdk.dev/providers/ai-sdk-providers/openai>
  - Anthropic: <https://v6.ai-sdk.dev/providers/ai-sdk-providers/anthropic>
  - xAI: <https://v6.ai-sdk.dev/providers/ai-sdk-providers/xai> (if unavailable, use OpenAI-compatible)
  - OpenRouter (community): <https://v6.ai-sdk.dev/providers/community-providers/openrouter>

## Tools to use

- exa.web_search_exa for latest PostgREST/Supabase security notes
- exa.crawling_exa for the above docs (claims/roles, provider pages)
- firecrawl_scrape as needed for specific pages
- exa.get_code_context_exa for Supabase JS examples and Next route patterns
- zen.planner for step-by-step with one in_progress
- zen.thinkdeep + zen.analyze for design/quality review
- zen.consensus for decisions (rate limits, RPC shape changes) with weighted scoring (≥ 9.0/10)
- zen.secaudit mandatory before marking complete (secrets, RPCs, SSR boundaries)
- zen.challenge for contentious assumptions
- zen.codereview prior to completion

## Plan (overview)

1) Crawl Supabase/PostgREST claims docs; verify RPC guard style
2) Implement server routes in Next.js:
   - `POST /api/keys` (body: { service, api_key }) → call `insert_user_api_key`
   - `DELETE /api/keys/[service]` → call `delete_user_api_key`
   - `POST /api/keys/validate` → attempt provider metadata call using AI SDK with supplied key; do NOT persist
3) Rate-limit POST/DELETE more strictly than chat
4) Telemetry spans around RPC calls; redact `api_key` in logs
5) Vitest tests: unit for RPC wrappers; integration with route handlers using Supabase client mocks and provider mocks
6) Codereview

## Checklist (mark off; add notes under each)

- [x] Draft ADR(s) and Spec(s) (pre-implementation; research + consensus)
  - Notes:
    - Added ADR `docs/adrs/adr-0024-byok-routes-and-security.md` and Spec `docs/specs/0011-spec-byok-routes-and-security.md` capturing design, contracts, rate limits, and testing.
- [x] Crawl Supabase/PostgREST claims docs; verify RPC guard style
  - Notes:
    - Verified `current_setting('request.jwt.claims', true)::jsonb->>'role'='service_role'` checks in SQL migrations.
- [x] Implement server routes:
  - [x] `POST /api/keys` (upsert via `insert_user_api_key`)
    - Notes:
      - Implemented at `frontend/src/app/api/keys/route.ts`; validates allowed services and requires auth; returns 204.
  - [x] `DELETE /api/keys/[service]` (delete via `delete_user_api_key`)
    - Notes:
      - Implemented at `frontend/src/app/api/keys/[service]/route.ts`; validates service; requires auth; returns 204.
  - [x] `POST /api/keys/validate` (AI SDK metadata check; no persist)
    - Notes:
      - Implemented at `frontend/src/app/api/keys/validate/route.ts`; performs minimal provider metadata check; requires auth; no persistence.
- [x] Add strict rate limits for POST/DELETE
  - Notes:
    - Upstash Ratelimit configured (env-gated). CRUD 10/min, validate 20/min per user. Reused `buildRateLimitKey`.
- [x] Add telemetry spans; redact `api_key` in logs
  - Notes:
    - Logging redacts secrets; only error messages are logged without key values.
- [x] Vitest tests: RPC wrappers + route handlers with mocks
  - Notes:
    - Added targeted tests under `frontend/src/lib/supabase/__tests__/rpc.test.ts`, `frontend/src/app/api/keys/**/__tests__/*`.
- [x] ESLint rule to restrict server-only imports
  - Notes:
    - Added `no-restricted-imports` to block `@/lib/supabase/admin` and `@/lib/supabase/rpc` in client code; allowed in `src/app/api/**`, `src/lib/supabase/**`, and tests via overrides.
- [x] Additional unit tests
  - Notes:
    - Added GET /api/keys tests in `frontend/src/app/api/keys/__tests__/get-route.test.ts` covering authenticated success and 401.
- [x] Codereview + finalize
  - Notes:
    - Addressed findings: added `server-only` guards, auth on validate, and service validation returning 400.
- [x] Finalize ADR(s) and Spec(s) for BYOK routes/security decisions
  - Notes:
    - Linked ADR/Spec from `docs/operators/security-guide.md`; added to ADR index.

## Working instructions (mandatory)

- Only check a task after Vitest, Biome/ESLint/Prettier, and `tsc --noEmit` are clean for changed scope.
- Under each task, record “Notes” for implementation details, issues, and tech debt addressed or scheduled.
- Address all security/tech debt encountered; otherwise log in Final Notes.
- Author ADR(s) in `docs/adrs/` capturing the BYOK architecture, RPC gating, rate-limits, and attribution of privileges. Write a full Spec in `docs/specs/` detailing route contracts, request/response schemas, error mapping, and testing strategy. Include links to zen.consensus outcomes and exa/firecrawl research.

## Process flow (required)

1) Research: Use exa.web_search_exa → exa.crawling_exa → firecrawl_scrape → exa.get_code_context_exa to gather latest guidance on PostgREST/Supabase security and AI SDK validation patterns. Summarize applicable patterns.
2) Plan: Use zen.planner with a single in_progress step; break work into atomic tasks (checkboxes) with clear deliverables.
3) Deep design: Run zen.thinkdeep + zen.analyze to document trade-offs (RPC shapes, rate limits, error mapping), data flow, and security boundaries (SSR-only, secrets handling).
4) Decide: Use zen.consensus and the Decision Framework (Solution Leverage 35, App Value 30, Maint. Load 25, Adaptability 10). Require ≥ 9.0/10 to proceed; otherwise revise design.
5) Draft docs: Write ADR(s) in docs/adrs/ and Spec(s) in docs/specs/ capturing the design, contracts, schemas, error policy, testing plan, telemetry. Link research and consensus outputs.
6) Security review: Run zen.secaudit on the draft design (routes, RPCs, secrets). Address findings before coding.
7) Implement: Build routes and RPC wrappers; write Vitest; ensure Biome/ESLint/Prettier and tsc --noEmit are clean throughout.
8) Challenge: Use zen.challenge to validate assumptions or risky areas discovered during implementation.
9) Review: Run zen.codereview; fix issues; re-run tests and static checks.
10) Finalize docs: Update ADR/Spec with implementation deltas, outcomes, and any follow-ups.

## Implementation detail

- Supabase client wrapper module: `frontend/lib/supabase/rpc.ts` with typed helpers:
  - `insertUserApiKey(userId, service, key)`
  - `deleteUserApiKey(userId, service)`
  - `touchUserApiKey(userId, service)` (for later usage updates)
- Route handlers:
  - Validate `service` ∈ {openai, openrouter, anthropic, xai}; return 400 on invalid.
  - Use server admin client; ensure SSR-only; never return secrets.
  - Validate: provider metadata call (AI SDK) with try/catch → { is_valid, reason }
- Rate-limits: Upstash or similar. Keep strict: e.g., 10/min per user for CRUD.
- Logging redaction: trim payloads; never serialize `api_key`.

## Quality gates

- `pnpm test` all BYOK tests green
- Validate route type-safety; no leakage of secrets

## Legacy mapping (delete later after app cutover)

- [x] `tripsage/api/routers/keys.py` and its unit tests (removed)
- [x] Python BYOK validation unit test `tests/unit/api/test_keys_validate_unit.py` (removed)
- [x] OpenAPI snapshot test normalized to ignore legacy `/api/keys*` paths

## Step-by-step

1) Research: exa.crawling_exa PostgREST roles docs; verify our SQL functions enforce claims guard
2) Code: create `lib/supabase/rpc.ts` + route handlers; add rate-limit middleware
3) Tests: unit for rpc wrappers (mock `createClient`), integration tests for handlers; provider validation mocks
4) zen.codereview → finalize

## Final Notes & Next Steps (compile from task notes)

- Summary of changes and decisions:
- Outstanding items / tracked tech debt:
- Follow-up prompts or tasks:

## Additional context & assumptions

- Supabase Vault RPCs (SQL already provisioned in `supabase/migrations/*vault_api_keys.sql`):
  - `insert_user_api_key(p_user_id UUID, p_service TEXT, p_api_key TEXT) RETURNS UUID`
  - `delete_user_api_key(p_user_id UUID, p_service TEXT) RETURNS VOID`
  - `get_user_api_key(p_user_id UUID, p_service TEXT) RETURNS TEXT`
  - `touch_user_api_key(p_user_id UUID, p_service TEXT) RETURNS VOID`
- PostgREST claims guard expected inside functions: `current_setting('request.jwt.claims', true)::jsonb->>'role' = 'service_role'`.
- The definer role must have minimal privileges and functions must be owned by that role; PUBLIC revoked from `vault` schema/tables.
- Server-only envs (do not expose to client): `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (naming per project conventions). Use Edge runtime if suitable; verify compatibility.

## File & module targets

- `frontend/app/api/keys/route.ts` (POST upsert)
- `frontend/app/api/keys/[service]/route.ts` (DELETE)
- `frontend/app/api/keys/validate/route.ts` (POST)
- `frontend/lib/supabase/server.ts` (admin client factory)
- `frontend/lib/supabase/rpc.ts` (typed wrappers for insert/delete/touch/get)

## Request/response shapes

- POST /api/keys
  - Body: `{ service: 'openai'|'openrouter'|'anthropic'|'xai', api_key: string }`
  - Response: `204 No Content` on success; `400` invalid service; `500` on RPC failure
- DELETE /api/keys/[service]
  - Response: `204 No Content` on success; `400` invalid service; `500` on failure
- POST /api/keys/validate
  - Body: `{ service: string, api_key: string }`
  - Response: `{ is_valid: boolean, reason?: string }` (never persists; provider mocked in tests)

## Error handling & mapping

- Normalize errors to `{ error: string, code?: string }` with appropriate HTTP status.
- Always redact `api_key` from logs; include `service`, `user_id`, and `request_id` metadata.

## Rate limits (suggested defaults)

- POST/DELETE /api/keys*: `10/minute` per user
- POST /api/keys/validate: `20/minute` per user

## Testing & mocking guidelines

- Supabase JS: mock `createClient`/admin client so RPC calls can be asserted without network.
- Provider validation: stub AI SDK provider calls; do not make live requests.
- Validate response codes, shapes, and rate-limit headers.
