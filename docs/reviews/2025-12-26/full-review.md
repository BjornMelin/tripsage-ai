# Repository Review – 2025-12-26

> Phase 1 (analysis-only). No source-code changes were made during this phase.
>
> **Repo state at time of review**
>
> - Worktree was **dirty** with a large set of local modifications/deletions (`git status -sb` showed many `M`/`D` entries, plus untracked `.knip-files.json`).
> - Baseline checks (run on 2025-12-26):
>   - `pnpm biome:check` ✅ (0 issues)
>   - `pnpm type-check` ✅ (0 issues)
>   - `pnpm test:affected` ✅ (exit 0; ~333 test files discovered; ~3342 tests executed; 3 skipped)

## 1. Executive Summary

- The repository is in **good operational shape** today: Biome, TypeScript, and the affected test suite all pass.
- The primary remaining work is **architectural debt and consistency** rather than “red CI” debt.
- The biggest themes observed:
  1. **Layering/boundary drift:** `src/domain/**` is inconsistent: some modules are clean/pure (e.g. flights), while others are tightly coupled to infra (`@/lib/*`) and even AI tooling (`@ai/tools/*`). This creates cognitive load and makes refactors risky.
  2. **Hidden module-scope state:** domain “containers” (`src/domain/*/container.ts`) use singletons and build infra objects once, which conflicts with the repo’s own guidance to construct dependencies inside handlers and to avoid module-scope state in server entrypoints.
  3. **Type escape hatches in production:** multiple production files use `as any` / `any` (some with `biome-ignore`) and `@ts-expect-error` to work around library typing gaps (Supabase realtime, AI SDK tool factories, etc.). This is manageable but should be systematically reduced.
  4. **Overgrown UI/stores:** several stores and client components are 650–850+ LOC, which is workable but makes changes expensive and increases regression risk.
  5. **Product TODOs / placeholders:** a few explicit TODOs and stubbed states remain in UI.
  6. **AI output rendering surface:** Streamdown defaults currently include raw HTML rendering (`rehype-raw`) for AI-generated markdown, which increases XSS risk unless paired with stronger sanitization (see TD-17).

**Overall technical debt assessment:** **Medium**  
Justification: core quality gates pass, but the architecture boundaries and typing escape hatches will accumulate compounding cost if left unaddressed.

## 2. Architecture and Design

### 2.1 Current Architecture Snapshot

- **Framework:** Next.js App Router (`src/app/**`), React 19, TypeScript (strict), Biome.
- **Backend/infra:** Supabase SSR (`src/lib/supabase/**`), Upstash (`src/lib/redis`, `src/lib/ratelimit`, `src/lib/cache`), OpenTelemetry helpers (`src/lib/telemetry/**`).
- **AI:** AI SDK v6 (`ai`), agent/tool infrastructure in `src/ai/**`; agent routes consolidated via `src/lib/api/factory.ts#createAgentRoute`.
- **Domain:** `src/domain/**` holds domain services and provider adapters; **in practice** these range from pure mapping/service functions (flights) to infra-heavy orchestrators (accommodations, activities).
- **State/UI:** Zustand stores in `src/stores/**`; large feature components in `src/components/features/**` and `src/app/dashboard/**`.
- **Testing:** Vitest multi-project config (`vitest.config.ts`) with `api`, `component (jsdom)`, `unit`, `schemas`, `integration`.

### 2.2 Key Strengths

- **Quality gates exist and pass** (Biome + TypeScript + affected tests).
- Strong investment in **in-repo enforcement scripts** (`scripts/check-*.mjs`) and test harness stability.
- Clear infra separation for many concerns (env validation, telemetry helpers, caching helpers).
- Many route handlers follow standardized patterns (`withApiGuards`, schema validation, and consistent error responses).

### 2.3 Key Issues and Anti-Patterns (Representative Examples)

1. **Domain → Infra / AI Coupling (inconsistent boundaries)**

- `src/domain/accommodations/service.ts` imports multiple `@/lib/*` infra modules directly (cache, Google APIs, retry, telemetry) and implements caching/rate-limit behavior inside the domain service.
- `src/domain/activities/service.ts` imports and calls an AI tool directly: `import { webSearch } from "@ai/tools/server/web-search";` (top of file).

Impact: the “domain” layer is no longer a stable abstraction boundary; it becomes harder to test in isolation, reuse, or refactor infra independently.

1. **Module-scope singleton containers**

- `src/domain/activities/container.ts`:

  ```ts
  let singleton: ActivitiesService | undefined;
  export function getActivitiesService(): ActivitiesService { ... }
  ```

- `src/domain/accommodations/container.ts` additionally instantiates a `Ratelimit` and caches the service.

Impact: implicit global state; harder to override deps in tests; diverges from the repo’s “construct per request inside handler” guidance.

1. **Route handler vs handler duplication**

- `src/app/api/chat/stream/route.ts` wraps POST in `withApiGuards({ auth: true, rateLimit: "chat:stream", ... })`.
- `src/app/api/chat/stream/_handler.ts` performs **another auth lookup** via `deps.supabase.auth.getUser()` and also contains an optional `deps.limit` rate-limiter path.

Impact: duplicated responsibilities, extra roundtrips, and risk of divergence in future changes.

1. **Error response consistency gap**

- `src/app/api/chat/stream/_handler.ts` constructs a raw `Response` for rate limiting to set `Retry-After` because `errorResponse()` doesn’t support custom headers:

  ```ts
  return new Response(JSON.stringify({ error: "rate_limited", ... }), { headers: { "Retry-After": "60" }, status: 429 });
  ```

Impact: inconsistent error response shape and bypass of standardized helpers. **However**, this is a symptom of duplicated responsibility: `withApiGuards` already enforces route rate limits and applies standardized rate limit headers (including `Retry-After`) via `applyRateLimitHeaders()`. The highest-leverage fix is to **remove handler-level rate limiting entirely** and rely on `withApiGuards` for 429 responses.

1. **AI markdown rendering allows raw HTML**

- `src/components/ai-elements/streamdown-config.ts` includes `defaultRehypePlugins.raw` (i.e., `rehype-raw`), enabling embedded HTML inside AI-generated markdown.

Impact: expands the client-side attack surface for prompt-injection / malicious model output (XSS and tracking vectors) unless paired with stronger sanitization. The recommended Phase 2 approach is to **disable raw HTML for AI output** (see TD-17 / D12).

### 2.4 Recommendations (Design-Level)

- **Clarify and enforce the boundary:** treat `src/domain/**` as “pure-ish” (schemas + domain logic), and push infra wiring + AI tool invocation into `src/lib/**` (or dedicated “application service” modules) that are explicitly `server-only`.
- Replace singleton “containers” with **factory functions** and construct dependencies inside the route handler adapter or `_handler.ts` adapter, consistent with repo patterns.
- Standardize route patterns:
  - `route.ts` = adapter (request parsing, SSR clients/ratelimiters created inside handler, no module-scope state)
  - `_handler.ts` = pure function with injected deps (no `process.env`, no module singletons)
- Reduce “type escape hatches” by creating **small typed wrappers** around known pain points (Supabase realtime overloads, AI SDK tool factory typing).

## 3. Code Quality and Code Smells

### 3.1 Hidden Global State / Singletons

- `src/domain/activities/container.ts` and `src/domain/accommodations/container.ts` use module-scoped singletons.
- Some server-only modules cache configuration/client state (e.g. `src/lib/env/server.ts` caches parsed env). This pattern is reasonable for env parsing, but domain/service singletons are harder to justify.

Recommended refactor:

- Replace singleton containers with `create*Service(deps)` factories.
- Initialize per request (or per handler invocation), passing deps explicitly.

### 3.2 Type Escape Hatches in Production

Examples:

- `src/hooks/supabase/use-realtime-channel.ts` uses `@ts-expect-error` and `(channel as any).on(...)` due to Supabase overload resolution.
- `src/hooks/use-zod-form.ts` uses `zodResolver(schema as any)` with a Biome ignore.
- `src/ai/tools/server/planning.ts` uses `any` (with Biome ignores) inside `combineSearchResults`.
- `src/ai/lib/tool-factory.ts` employs `(tool as any)(...)` to work around AI SDK inference limitations.

Recommended refactor:

- Add a typed wrapper utility for Supabase realtime `.on(...)`.
- Use Zod-inferred types for tool input/output to eliminate `any` in tool implementations.
- Where unavoidable, isolate the assertion to a single helper with a clear comment and tests.

### 3.3 Overgrown Modules (Maintainability Hotspots)

Top large files (by LOC; generated files excluded from “smell” severity):

- `src/lib/api/factory.ts` (~771) – acceptable as a central “API/Agent route factory”, but still a refactor hotspot.
- `src/ai/lib/tool-factory.ts` (~654) – central abstraction; risk when changing.
- Stores/components at 650–850+ LOC:
  - `src/app/dashboard/search/hotels/hotels-search-client.tsx` (~677)
  - `src/app/dashboard/search/activities/activities-search-client.tsx` (~759)
  - `src/components/features/search/forms/destination-search-form.tsx` (~849)
  - `src/stores/budget-store.ts` (~725)
  - `src/stores/search-results-store.ts` (~678)
  - `src/stores/search-filters-store.ts` (~722)

Recommended refactor:

- Extract subcomponents (UI) and “pure” helpers (formatting, mapping) into adjacent modules.
- For large Zustand stores, move to slice composition under `src/stores/<feature>/**` per repo standards.

### 3.4 Inconsistent Domain Purity

- Flights domain (`src/domain/flights/**`) is clean: validated input, provider call, mapping, Zod-validated output.
- Activities/accommodations domains perform infra orchestration internally, mixing caching, provider calls, enrichment, and AI fallback.

Recommended refactor:

- Converge on the flights pattern: domain functions/classes receive injected “ports” and remain deterministic; infra wiring belongs to app/lib adapters.

## 4. Duplication and Consolidation Opportunities

1) **Rate-limiting logic duplication**

- `src/lib/api/factory.ts`: `enforceRateLimit(...)` for routes with degrade-mode semantics.
- `src/ai/lib/tool-factory.ts`: `enforceRateLimit(...)` for tools, including identifier extraction and Upstash limiter caching.
- `src/domain/accommodations/service.ts`: optional internal rate limiting via injected `Ratelimit`.

Recommendation:

- Extract a shared `src/lib/ratelimit/enforce.ts` (or similar) with common primitives (identifier normalization/hashing, limiter caching, reset normalization), then keep policy decisions (route keys, degraded modes) local.

1) **Error response helper gaps**

- Observed gap: `src/app/api/chat/stream/_handler.ts` creates a raw `Response` to attach `Retry-After`.
- Research-backed correction: the repo already has a rate limit header utility (`src/lib/ratelimit/headers.ts`) and `withApiGuards` already applies headers for route rate limits. Prefer **removing the redundant handler-level rate limiting** over extending `errorResponse()` to accept headers.

1) **Env access patterns**

- Validated env helpers exist (`src/lib/env/server.ts`, `src/lib/env/client.ts`), but several modules still access `process.env` directly for non-trivial keys (e.g. `src/lib/memory/mem0-adapter.ts`).

Recommendation:

- Standardize on env helpers; keep exceptions for performance/bootstrapping only with explicit comments.

## 5. KISS, DRY, YAGNI Issues

### 5.1 KISS (Unnecessary Complexity)

- `src/ai/agents/chat-agent.ts` contains substantial custom logic for token budgeting and context compression. This may be justified, but it’s complex enough that it should be:
  - Extracted into a dedicated module
  - Covered by focused tests
  - Documented as a deliberate design choice

### 5.2 DRY (Repeated Responsibility / Overlap)

- Chat stream auth + rate-limiting are implemented in both `withApiGuards` and `handleChatStream`.
- Rate-limiting logic exists in multiple layers (route factory, tool factory, domain services).

### 5.3 YAGNI (Speculative/Incomplete Features)

- `src/app/dashboard/search/hotels/hotels-search-client.tsx` has a TODO to fetch personalized tips; currently static tips are fine and could be left as-is without a TODO.
- `src/app/dashboard/trips/[id]/collaborate/page.tsx` used a stubbed collaborators state with TODO at review time; this is now implemented in Phase 2 (see **9.B**, TD-12/D10).

## 6. Technical Debt Inventory (MUST BE FULLY ADDRESSED)

> Each item below must be either fixed in Phase 2 or explicitly retained as deliberate debt with rationale.

### Architecture and Design Debt

- **TD-1** – Domain layer coupled to infra and AI tooling  
  - **Files:** `src/domain/accommodations/service.ts`, `src/domain/accommodations/providers/amadeus-adapter.ts`, `src/domain/activities/service.ts`  
  - **Problem:** domain code imports `@/lib/*` directly and (for activities) calls AI tools.  
  - **Risk/impact:** **High** (boundary drift; testing/refactoring cost).  
  - **Resolution:** inject infra “ports” (cache, geocoding/enrichment, retries, logging) and move orchestration/wiring to app/lib layer; remove `@ai/tools/*` from `src/domain/**`.

- **TD-2** – Module-scope singleton “containers” in domain  
  - **Files:** `src/domain/activities/container.ts`, `src/domain/accommodations/container.ts`  
  - **Problem:** global singletons and cached infra objects.  
  - **Risk/impact:** **Medium** (implicit state; harder tests; inconsistent with guidance).  
  - **Resolution:** replace with `create*Service()` factories; initialize per-request in route adapters.

- **TD-3** – Chat stream route/handler duplicate auth and optional rate-limiting  
  - **Files:** `src/app/api/chat/stream/route.ts`, `src/app/api/chat/stream/_handler.ts`  
  - **Problem:** auth is enforced in both layers; handler retains unused optional rate-limiting.  
  - **Risk/impact:** **Medium** (duplication and inconsistency).  
  - **Resolution:** make `_handler.ts` accept `userId` (or user) from `withApiGuards`, remove internal auth and rate-limiting logic from handler.

- **TD-4** – Rate-limiting duplication across layers  
  - **Files:** `src/lib/api/factory.ts`, `src/ai/lib/tool-factory.ts`, plus domain services using `Ratelimit`  
  - **Problem:** multiple implementations of identifier selection, limiter caching, and response formatting.  
  - **Risk/impact:** **Medium** (inconsistent throttling semantics; hard to evolve).  
  - **Resolution (refined):** keep **separate** enforcement paths for HTTP routes vs AI tools (different error/reporting contracts), but ensure they share the same primitives where it matters:
    - Identifier normalization/hashing already shared via `src/lib/ratelimit/identifier.ts`.
    - HTTP responses should continue to use `applyRateLimitHeaders()` / `src/lib/ratelimit/headers.ts`.
    - Tool errors should continue to include retry metadata in `ToolError` for UI/tooling handling.
    - In Phase 2: either extract any remaining truly-shared logic (only if it reduces complexity), or explicitly document the deliberate duplication and why it is retained (KISS).

### Type-system and Typing Debt

- **TD-5** – `@ts-expect-error` and `as any` in Supabase realtime hook  
  - **Files:** `src/hooks/supabase/use-realtime-channel.ts`  
  - **Problem:** TS overload mismatch is bypassed with `@ts-expect-error` (broadcast subscription with runtime event names) and `(channel as any).on(...)` (postgres_changes subscription with runtime-computed event types).  
  - **Risk/impact:** **Medium** (type drift can silently break runtime assumptions).  
  - **Resolution (research-backed; revised after deeper SDK type review):** eliminate escape hatches **without widening subscriptions** by aligning our generics/callback types with the official `RealtimeChannel.on(...)` overloads.
    - **Broadcast typing fix (no wildcard required):**
      - Constrain the generic payload type to `Record<string, unknown>` (Supabase broadcast overload uses `T extends { [key: string]: any }`).
      - Type the callback parameter to match the broadcast overload shape (includes `{ type: 'broadcast'; event: string; payload: T; meta?: ... }`) so TypeScript selects the correct overload.
      - Keep current per-event filtering at the socket level (`{ event: eventName }`) to avoid extra bandwidth.
    - **Postgres changes typing fix (no `any` required):**
      - Avoid passing a union-typed `event` into `.on(...)` (it prevents overload selection). Use a small `switch` on the event value to call `.on(...)` with **literal** `"INSERT" | "UPDATE" | "DELETE" | "*"` in each branch.
      - Keep server-side filtering via `{ schema, table, filter }` unchanged (no broadening).
    - Evidence:
      - Supabase docs allow `event: '*'` for both broadcast and Postgres Changes (useful as fallback but not required for typing): `https://supabase.com/docs/guides/realtime/broadcast`, `https://supabase.com/docs/guides/realtime/postgres-changes`
      - Supabase JS SDK source shows the relevant overload constraints and event handling: `https://github.com/supabase/supabase-js/blob/master/packages/core/realtime-js/src/RealtimeChannel.ts`

- **TD-6** – Production `any` usage / Biome ignores for complex structures  
  - **Files:** `src/ai/tools/server/planning.ts` (combine results), `src/hooks/use-zod-form.ts`, `src/components/features/search/common/use-search-form.ts`, `src/ai/lib/tool-factory.ts`, `src/lib/supabase/typed-helpers.ts`  
  - **Problem:** “escape hatches” reduce type safety and make refactors riskier.  
  - **Risk/impact:** **Medium**.  
  - **Resolution:** remove `any` where feasible via Zod-inferred types and better generics; if not feasible, isolate and document as deliberate debt.

- **TD-7** – Zod v4 option style mismatch (`message` vs `error`)  
  - **Files:** `src/ai/tools/schemas/google-places.ts`  
  - **Problem:** `.refine(..., { message: ... })` violates the repo’s Zod v4 conventions.  
  - **Risk/impact:** **Low** (style consistency).  
  - **Resolution:** switch to `{ error: ... }` per conventions.

### Testing and Coverage Debt

- **TD-8** – Tests use `as unknown as` / `as any` instead of `unsafeCast<T>()`  
  - **Files:** `src/app/api/chat/stream/__tests__/route.smoke.test.ts` (e.g. `as unknown as LanguageModel`), plus a few `as any` uses in tests.  
  - **Risk/impact:** **Low**.  
  - **Resolution:** replace with `unsafeCast<T>()` to keep test typing patterns consistent.

- **TD-9** – Coverage thresholds below stated policy target  
  - **Files:** `vitest.config.ts` (thresholds: branches 35, functions 50, lines 45, statements 45)  
  - **Risk/impact:** **Medium** (coverage baseline may hide regressions).  
  - **Resolution:** raise thresholds incrementally and add targeted tests for critical flows (especially around boundary/infra code).

### Tooling / Documentation Debt

- **TD-10** – Version contract mismatch (AI SDK “exact betas” vs actual deps)  
  - **Files:** `docs/architecture/frontend-architecture.md`, `docs/architecture/system-overview.md`, `docs/development/core/development-guide.md`, `docs/development/README.md`, `docs/api/README.md`, `docs/review/2025-12-15/implementation-guide.md`, `docs/review/2025-12-15/review-log.md`  
  - **Problem:** several docs still reference **AI SDK v6 beta** pins and beta-only doc links, while `package.json` (and `AGENTS.md`) now uses **AI SDK v6 stable** versions (e.g. `ai@6.0.3`, `@ai-sdk/react@3.0.3`, `@ai-sdk/openai@3.0.1`, `@ai-sdk/anthropic@3.0.1`, `@ai-sdk/xai@3.0.1`).  
  - **Risk/impact:** **Low/Medium** (confusion and wrong assumptions in reviews).  
  - **Resolution:** treat `package.json` (and the pinned versions in `AGENTS.md`) as the source of truth; update version references and doc links elsewhere to either (a) match reality, or (b) avoid pinning versions in prose and instead point to the canonical source.

- **TD-11** – Architecture burn-down TODOs in scripts  
  - **Files:** `scripts/check-boundaries.mjs` (TODO ARCH-001), `scripts/check-ai-tools.mjs` (TODO ARCH-002)  
  - **Risk/impact:** **Low** (currently mostly informational).  
  - **Resolution:** either remove TODO markers if no allowlist exists, or convert into a tracked list with explicit owners/targets.

### Product / UX Debt

- **TD-12** – UI TODOs / placeholders  
  - **Files:** `src/app/dashboard/search/hotels/hotels-search-client.tsx` (tips TODO); `src/app/dashboard/trips/[id]/collaborate/page.tsx` (stub collaborators, **resolved in Phase 2** — see **9.B**)  
  - **Risk/impact:** **Low/Medium** (user-facing incompleteness).  
  - **Resolution:** implement the missing hook/API or remove/replace stubs with explicit “Coming soon” UX and remove TODO noise.

### Maintainability Debt

- **TD-13** – Large stores and components exceeding slice guidance  
  - **Files:** `src/stores/budget-store.ts`, `src/stores/search-results-store.ts`, `src/stores/search-filters-store.ts`, plus large dashboard clients under `src/app/dashboard/search/**`  
  - **Risk/impact:** **Medium** (harder refactors; higher bug risk).  
  - **Resolution:** split into store slices and UI subcomponents; extract pure helpers; add tests for extracted logic.

- **TD-14** – Minor type hack in accommodations service (span type extraction)  
  - **Files:** `src/domain/accommodations/service.ts`  
  - **Risk/impact:** **Low**.  
  - **Resolution:** import `type Span` from `@/lib/telemetry/span` directly and remove the extraction hack.

- **TD-15** – Direct `process.env` access bypassing env helpers in some server-only modules  
  - **Files (primary candidates):**
    - `src/lib/memory/mem0-adapter.ts` (`MEM0_API_KEY`)
    - `src/domain/amadeus/client.ts` (`AMADEUS_ENV`)
    - `src/config/bot-protection.ts` (`BOTID_ENABLE`)
    - `src/lib/idempotency/redis.ts` (`IDEMPOTENCY_FAIL_OPEN`)
    - `src/lib/telemetry/constants.ts` (`TELEMETRY_SILENT`)
    - `src/lib/http/ip.ts` (`VERCEL`, `TRUST_PROXY`)
  - **Allowed exceptions (not TD):** `src/lib/env/**` itself, plus `process.env.NODE_ENV` / `NEXT_PHASE` / `NEXT_RUNTIME` guards (compile/build/runtime behavior).
  - **Risk/impact:** **Medium** (inconsistent validation and build-time safety).  
  - **Resolution:** use `getServerEnvVarWithFallback` / `getServerEnv` and client env helpers consistently; document any intentional exceptions.

- **TD-16 (UNVERIFIED)** – Potential unused dependencies / dead code  
  - **Evidence:** `knip.json` exists and `.knip-files.json` is present in the worktree; no fresh Knip run was performed in Phase 1 to avoid generating additional artifacts.  
  - **Risk/impact:** **Low/Medium**.  
  - **Resolution:** run `pnpm deps:report` / `pnpm deps:audit` in Phase 2 and remove unused deps/files.

### Security / Content Rendering Debt

- **TD-17** – Streamdown raw HTML enabled for AI-generated markdown (potential XSS surface)  
  - **Files:** `src/components/ai-elements/streamdown-config.ts`, `src/components/ai-elements/response.tsx`, `src/components/chat/message-item.tsx`  
  - **Problem:** Streamdown’s default plugins include `rehype-raw` (`defaultRehypePlugins.raw`). For **untrusted AI output**, raw HTML rendering is a high-risk surface unless paired with an HTML sanitizer. Our current config uses `rehype-harden` (protocol/prefix hardening) but does **not** include `rehype-sanitize`.  
  - **Risk/impact:** **High** (client-side XSS + content exfil/track vectors via injected HTML).  
  - **Resolution (finalized; see D12):** disable raw HTML for AI markdown by omitting `defaultRehypePlugins.raw`; keep `defaultRehypePlugins.katex` + `rehype-harden` with `allowedProtocols` + `allowDataImages:false`. If trusted HTML is ever needed, introduce a separate “trusted markdown renderer” that uses `rehype-sanitize` **after** raw.  
  - **Evidence:**
    - Streamdown docs show how to disable HTML by omitting `raw`: `https://streamdown.ai/docs/security#html-content`
    - Vercel markdown-sanitizers warns `rehype-raw` must be paired with `rehype-sanitize` for untrusted content: `https://github.com/vercel-labs/markdown-sanitizers#️-important-use-rehype-sanitize-if-using-rehype-raw`

## 7. Linting, Formatting, and TypeScript Issues

### 7.1 Biome

- Current status: **clean** (`pnpm biome:check` passed).
- Observed pattern: a few **explicit suppressions** exist in production code for legitimate typing gaps (AI SDK / Supabase).
- Tests relax `noExplicitAny` to **warn** via Biome overrides (`biome.json`), which is acceptable but should remain tightly scoped.

Plan:

- Prefer removing suppressions by introducing typed wrappers. Where suppressions remain, keep them localized and add justification comments (not “because it’s complex”).

### 7.2 TypeScript

- Current status: **clean** (`pnpm type-check` passed).
- Main risk is not “red TS”, but **type safety drift** due to local `as any` / `@ts-expect-error` workarounds.

Plan:

- Replace `@ts-expect-error` with typed helpers where possible.
- Reduce `as any` usage in production paths; keep test-only casting via `unsafeCast`.

## 8. Testing and Reliability

- Current status: **clean** (`pnpm test:affected` passed).
- Test organization is strong (separate projects by runtime/environment).
- Recommended improvements:
  - Add focused tests for high-complexity logic that currently lives inside large modules (e.g., chat context compression in `src/ai/agents/chat-agent.ts`).
  - Incrementally raise coverage thresholds once targeted tests exist (align with `docs/development/testing/coverage-milestones.md` intent).

## 9. Implementation Plan and Checklist

> Phase 2 executes this checklist. Every TD item above is mapped to one or more tasks below.

### 9.0 Decision Log (Finalized; research-backed)

> **Rubric (required):** Solution Leverage 35% · Application Value 30% · Maintenance/Cognitive Load 25% · Adaptability 10%  
> **Weighted score formula:** `0.35×SL + 0.30×AV + 0.25×MCL + 0.10×Ada`  
> **Finalization threshold:** weighted score **≥ 9.0 / 10.0**.
>
> **Zen validation note (Phase 1 extension):**
>
> - `zen.analyze` (gemini3-flash) validated the key architectural themes (domain boundary drift/singletons, chat handler duplication, Supabase Realtime typing escape hatches) and also flagged Streamdown raw-HTML rendering + collaboration UI stubs as notable risk surfaces.
> - `zen.consensus` consulted `gemini3` and `grok-4.1-openrouter` to finalize D9–D12. All decisions in this table meet the **≥ 9.0** threshold; where models disagreed (D11), we chose the KISS option that preserves the guardrail without adding expiration machinery.

| ID | Decision | Final option (Phase 2) | Weighted score | Status |
|---:|---|---|---:|---|
| D1 | Domain boundary remediation (TD-1/TD-2) | **Functional Core + Imperative Shell (scope-limited):** refactor **only** `src/domain/accommodations/**` + `src/domain/activities/**` toward the `src/domain/flights/service.ts` pattern by (a) moving infra wiring to route/tool adapters and (b) injecting side effects as plain functions (not “interface explosion” ports); remove domain singletons. | **9.2** | Finalized |
| D2 | Chat stream DRY (TD-3) | **Single owner for auth + route rate limits:** `withApiGuards` owns auth + route rate limiting; `_handler.ts` becomes a pure DI handler that receives `context.user`/`userId` and never calls `supabase.auth.getUser()` or performs rate limiting. | **9.6** | Finalized |
| D3 | Supabase Realtime typing (TD-5) | **Overload-aligned typing (no subscription widening):** eliminate `@ts-expect-error` and `(channel as any).on(...)` by matching Supabase SDK overload constraints (payload must be object) and using literal event values to select the correct overloads. Keep socket-level filtering (`{ event: 'shout' }`, `{ event: 'INSERT' }`) intact. | **9.1** | Finalized |
| D4 | RHF + Zod v4 resolver typing (TD-6) | **Centralize schema-derived generics:** remove `schema as any` by applying the resolvers-documented `useForm<z.input<typeof schema>, any, z.output<typeof schema>>({ resolver: zodResolver(schema) })` pattern **inside** `useZodForm` + `useSearchForm`, so feature call sites remain simple. | **9.1** | Finalized |
| D5 | AI SDK version reference alignment (TD-10) | **Single source of truth + drift guard:** treat `package.json` + `AGENTS.md` as canonical; update other docs that still mention beta pins / beta doc links (see TD-10). Add a lightweight script check to prevent future drift. | **9.1** | Finalized |
| D6 | Rate-limit error shaping | **No new error helper surface:** remove the redundant handler-level 429 path rather than extending `errorResponse()`; route-level rate limiting already applies standard headers via `applyRateLimitHeaders()`. | **9.1** | Finalized |
| D7 | AI SDK tool factory typing (`tool as any`) | **Improve only if simpler:** attempt a schema-driven `createAiTool` typing refactor to remove `(tool as any)` **only if** it reduces (not increases) complexity; otherwise keep a single localized cast with explicit justification + tests and treat as deliberate debt. | **9.0** | Finalized |
| D8 | Coverage thresholds (TD-9) | **Incremental increases tied to tests:** raise coverage thresholds in small steps only after adding targeted tests for critical/high-complexity logic; avoid a big-bang “85% now” jump. | **9.0** | Finalized |
| D9 | “Personalized tips” TODO (TD-12) | **Remove TODO; keep static tips:** remove the placeholder TODO and ensure copy doesn’t imply personalization. | **9.3** | Finalized |
| D10 | Collaboration page stubs (TD-12) | **Implement real collaboration:** replace stubbed invite/state with real collaborators CRUD + roles + real-time activity and permission-gated live editing (RLS-first). | **9.3** | Finalized |
| D11 | `TODO(ARCH-001/002)` allowlist markers (TD-11) | **Remove TODO markers; keep allowlists:** preserve the allowlist mechanism but require each entry to include a concrete justification + tracking issue (no expiration enforcement). | **9.3** | Finalized |
| D12 | Streamdown raw HTML (TD-17) | **Disable raw HTML for AI markdown:** omit `defaultRehypePlugins.raw` in shared defaults; keep KaTeX + harden protocol restrictions and `allowDataImages:false`. | **9.8** | Finalized |

#### 9.0.1 Scoring Breakdown (for auditability)

> Scores are 0–10 per criterion; weighted score uses the formula above.

| ID | SL | AV | MCL | Ada | Weighted |
|---:|---:|---:|---:|---:|---:|
| D1 | 9.5 | 9.0 | 9.0 | 9.0 | 9.2 |
| D2 | 9.5 | 9.5 | 10.0 | 9.0 | 9.6 |
| D3 | 9.0 | 9.0 | 9.5 | 9.0 | 9.1 |
| D4 | 9.0 | 9.0 | 9.5 | 9.0 | 9.1 |
| D5 | 9.0 | 9.0 | 9.5 | 9.0 | 9.1 |
| D6 | 9.0 | 9.0 | 9.5 | 9.0 | 9.1 |
| D7 | 9.0 | 9.0 | 9.0 | 9.0 | 9.0 |
| D8 | 9.0 | 8.5 | 10.0 | 9.0 | 9.1 |
| D9 | 10.0 | 8.0 | 10.0 | 9.0 | 9.3 |
| D10 | 10.0 | 8.0 | 10.0 | 9.0 | 9.3 |
| D11 | 10.0 | 8.0 | 10.0 | 9.0 | 9.3 |
| D12 | 10.0 | 10.0 | 10.0 | 8.0 | 9.8 |

**Primary sources and repo evidence used to finalize decisions**

- AI SDK 6 announcement + release date (Dec 22, 2025): `https://vercel.com/blog/ai-sdk-6`
- AI SDK v6 reference (`createAgentUIStreamResponse` signature, `uiMessages`, `headers`, `includeUsage`, `abortSignal`): `https://v6.ai-sdk.dev/docs/reference/ai-sdk-core/create-agent-ui-stream-response`
- AI SDK v6 reference (`tool()` signature: `inputSchema`, `execute`, `ToolExecutionOptions`): `https://ai-sdk.dev/docs/reference/ai-sdk-core/tool`
- AI SDK 5→6 migration guide (ToolLoopAgent; async `convertToModelMessages`): `https://ai-sdk.dev/docs/migration-guides/migration-guide-6-0`
- Supabase Realtime Broadcast docs (explicitly: event can be `*`): `https://supabase.com/docs/guides/realtime/broadcast`
- Supabase Realtime Postgres Changes docs (explicitly: event `*` supported): `https://supabase.com/docs/guides/realtime/postgres-changes`
- supabase-js tests confirm wildcard broadcast semantics: `https://github.com/supabase/supabase-js/blob/master/packages/core/realtime-js/test/RealtimeChannel.memory.test.ts`
- Supabase JS SDK source (`RealtimeChannel.on` overloads; broadcast payload constraint): `https://github.com/supabase/supabase-js/blob/master/packages/core/realtime-js/src/RealtimeChannel.ts`
- Upstash Ratelimit TS docs (`pending` + `context.waitUntil(pending)` for Edge/serverless): `https://upstash.com/docs/redis/sdks/ratelimit-ts/methods`
- Streamdown security hardening (`rehype-harden`): `https://github.com/vercel/streamdown/blob/main/apps/website/content/docs/security.mdx`
- Streamdown default plugins + configuration (`rehype-raw` is default): `https://streamdown.ai/docs/configuration`
- Streamdown security doc (`HTML Content` section shows omitting `raw`): `https://streamdown.ai/docs/security#html-content`
- Vercel markdown-sanitizers warning about `rehype-raw` + `rehype-sanitize`: `https://github.com/vercel-labs/markdown-sanitizers#️-important-use-rehype-sanitize-if-using-rehype-raw`
- Real-world Streamdown usage omitting `raw` to avoid interpreting HTML tags: `https://github.com/prowler-cloud/prowler/blob/master/ui/components/lighthouse/message-item.tsx`
- Next.js Route Handlers (adapter model; caching rules; `use cache` must be in helper): `https://nextjs.org/docs/app/getting-started/route-handlers`
- Next.js `use cache` directive (runtime APIs must be passed as args; Route Handlers must extract cached helper): `https://nextjs.org/docs/app/api-reference/directives/use-cache`
- Next.js Vitest guide (async Server Components limitation): `https://nextjs.org/docs/app/guides/testing/vitest`
- React Hook Form resolvers README (explicit `z.input`/`z.output` generics pattern): `https://github.com/react-hook-form/resolvers/blob/master/README.md`
- Zod v4 error option (`message` → `error`) guidance: `https://github.com/colinhacks/zod/blob/v4.0.1/packages/docs/content/v4/index.mdx`
- Vitest coverage thresholds config docs: `https://github.com/vitest-dev/vitest/blob/v4.0.7/docs/config/index.md`
- Vercel AI SDK example routes (real-world `createAgentUIStreamResponse` usage in Next.js App Router):
  - `https://github.com/vercel/ai/blob/main/examples/next-agent/app/api/chat/route.ts`
  - `https://github.com/vercel/ai/blob/main/examples/next-openai/app/api/chat-xai-web-search/route.ts`
- Repo evidence:
  - Route guardrails + standardized 429 headers: `src/lib/api/factory.ts`
  - Standard rate-limit headers helper: `src/lib/ratelimit/headers.ts`
  - “No new domain→infra imports” burn-down guard: `scripts/check-no-new-domain-infra-imports.mjs`
  - Reference “pure-ish domain” service: `src/domain/flights/service.ts`
  - Chat stream duplication currently present: `src/app/api/chat/stream/route.ts`, `src/app/api/chat/stream/_handler.ts`

### 9.A Outstanding Work (Remaining)

### 9.2 Architecture & Boundaries

- [ ] Remove domain singleton containers (Architecture) — refs: TD-2 — Priority: High
  - [ ] Delete `src/domain/activities/container.ts`
  - [ ] Delete `src/domain/accommodations/container.ts`
  - [ ] Replace all call sites (construct deps inside handler / tool execute):
    - [ ] `src/app/api/activities/search/route.ts`
    - [ ] `src/app/api/activities/[id]/route.ts`
    - [ ] `src/app/api/accommodations/search/route.ts`
    - [ ] `src/app/dashboard/search/unified/actions.ts`
    - [ ] `src/ai/tools/server/activities.ts`
    - [ ] `src/ai/tools/server/accommodations.ts`
  - [ ] Verify no remaining usage: `rg "getActivitiesService\\(|getAccommodationsService\\(" src` returns 0 matches
  - **Done when:** containers removed + all above call sites use explicit factories/constructors without module-scope singletons.

- [ ] Activities domain: isolate infra + AI tooling behind injected deps (Architecture) — refs: TD-1 — Priority: High
  - **Goal:** `src/domain/activities/**` should only import from `@domain/*` and `@schemas/*` (and local `./*`), mirroring the `src/domain/flights/service.ts` pattern.
  - [ ] Refactor `src/domain/activities/service.ts`:
    - [ ] Remove direct import of `@ai/tools/server/web-search` (inject a `webSearch` function/adapter instead)
    - [ ] Remove direct imports of `@/lib/google/places-activities` (inject Places search/detail fns)
    - [ ] Remove direct imports of `@/lib/*` infra helpers (hashing, logging, telemetry) by injecting the minimal functions needed
    - [ ] Ensure all non-determinism is injectable (`clock`, `id` generator) for tests
  - [ ] Update entrypoints to provide the adapters (no module-scope wiring):
    - [ ] `src/app/api/activities/search/route.ts`
    - [ ] `src/app/api/activities/[id]/route.ts`
    - [ ] `src/ai/tools/server/activities.ts`
  - [ ] Add/update focused tests for the extracted “core” logic (fallback trigger rules; cache hit/miss shaping) using fakes instead of network — refs: TD-9 — suggested location: `src/domain/activities/service.test.ts`
  - **Done when:** `src/domain/activities/service.ts` no longer imports `@ai/tools/*` or `@/lib/*`, and `pnpm check:no-new-domain-infra-imports` stays green.

- [ ] Accommodations domain: isolate infra behind injected deps (Architecture) — refs: TD-1, TD-14 — Priority: High
  - **Goal:** converge on the `flights` style: domain logic + provider adapter(s) with infra wiring in entrypoints.
  - [ ] Fix TD-14 while refactoring: remove the Telemetry span type extraction hack and use a direct type import from `@/lib/telemetry/span`.
  - [ ] Refactor `src/domain/accommodations/service.ts`:
    - [ ] Remove direct imports of cache helpers (`@/lib/cache/*`) by injecting cache get/set/versioning functions
    - [ ] Remove direct imports of Google geocoding/enrichment (`@/lib/google/*`) by injecting adapters
    - [ ] Remove direct import of retry helper (`@/lib/http/retry`) by injecting `retry` function
    - [ ] Move rate limiter creation out of the domain service (rate limiting should live in route/tool guards)
  - [ ] Update entrypoints to provide the adapters:
    - [ ] `src/app/api/accommodations/search/route.ts`
    - [ ] `src/app/dashboard/search/unified/actions.ts`
    - [ ] `src/ai/tools/server/accommodations.ts`
  - [ ] Add/update tests around the domain contract (cache-aside correctness; error mapping) using fake adapters
  - **Done when:** `src/domain/accommodations/service.ts` no longer imports `@/lib/cache/*`, `@/lib/google/*`, or `@/lib/http/retry`, and behavior is preserved via tests.

- [ ] Standardize route handlers to construct deps inside handler (Architecture) — refs: TD-2, TD-1 — Priority: High
  - [ ] Audit `src/app/api/**/route.ts` for module-scope service instances/clients
  - [ ] Ensure per-request construction for anything request-scoped (Supabase SSR clients, user-dependent configs)
  - [ ] For safe singleton reuse (e.g., pure config constants), document rationale
  - **Done when:** no route handler imports a domain singleton container; construction patterns match `withApiGuards` expectations.

### 9.3 Chat Stream Consistency

- [ ] Consolidate chat stream auth/rate-limiting responsibilities (DRY) — refs: TD-3 — Priority: High
  - [ ] Update `src/app/api/chat/stream/_handler.ts` to accept `user` (from `withApiGuards` context) rather than calling `deps.supabase.auth.getUser()`
  - [ ] Remove `deps.limit` from `ChatDeps` and delete the dead handler-level rate limit branch (no raw `new Response(...)` 429)
  - [ ] Wire abort handling using AI SDK v6 support:
    - [ ] Pass `abortSignal: req.signal` (or equivalent) into `createAgentUIStreamResponse(...)` to cancel streaming on disconnect (see AI SDK v6 ref in Decision Log)
  - [ ] Ensure all error responses use the standardized helpers (`unauthorizedResponse`, `errorResponse`) and that route-level rate limiting still sets headers via `applyRateLimitHeaders()`
  - [ ] Update tests for chat stream route and handler:
    - [ ] `src/app/api/chat/stream/__tests__/route.smoke.test.ts` (adjust mocks so auth is checked once at the guard level)
    - [ ] Add a regression test that aborting the request stops the stream (if feasible in current test harness)
  - **Done when:** `_handler.ts` contains no `supabase.auth.getUser()` and no handler-level rate limit code path; all affected tests pass.

### 9.4 Rate Limiting Consolidation

- [ ] Audit rate limiting duplication and either consolidate further or document deliberate duplication (KISS) — refs: TD-4 — Priority: Medium
  - [ ] Document the current split:
    - HTTP routes: `withApiGuards` / `src/lib/api/factory.ts` (error responses + headers via `applyRateLimitHeaders()`)
    - AI tools: `createAiTool` / `src/ai/lib/tool-factory.ts` (tool error shapes via `ToolError`)
  - [ ] Identify any truly duplicated “primitives” worth extracting (only if it reduces code):
    - Identifier normalization/hashing (already shared via `src/lib/ratelimit/identifier.ts`)
    - Retry-after computation and window parsing
  - [ ] If extracting, keep it tiny (one helper module) and keep policy decisions local (KISS)
  - [ ] If not extracting, document the deliberate duplication and why (different response contracts)
  - **Done when:** TD-4 has an explicit final state: consolidated where it helps, or documented deliberate split.

### 9.5 Type Safety Improvements (Production)

- [ ] Supabase Realtime: remove typing escape hatches **without widening subscriptions** (Typing) — refs: TD-5 — Priority: High
  - **Docs:** Supabase Broadcast + Postgres Changes, plus SDK source overloads: see links in **9.0**.
  - [ ] Broadcast path (`useRealtimeChannel`):
    - [ ] Constrain `Payload` to `Record<string, unknown>` to satisfy Supabase’s generic constraint (`T extends { [key: string]: any }`)
    - [ ] Type the callback parameter to match the broadcast overload shape so TS selects the right overload
    - [ ] Remove `@ts-expect-error` and any custom payload typing that conflicts with SDK overloads
  - [ ] Postgres changes path (`usePostgresChangesChannel`):
    - [ ] Remove `(channel as any).on(...)`
    - [ ] Use a `switch` on the `event` value to call `.on('postgres_changes', { event: 'INSERT' | 'UPDATE' | 'DELETE' | '*' ... })` with **literal** event strings (enables overload selection)
  - **Done when:** `src/hooks/supabase/use-realtime-channel.ts` has no `@ts-expect-error` and no `any` casts around `.on(...)`, and TypeScript passes.

- [ ] Remove `any` in `combineSearchResults` by using schema-inferred types (Typing) — refs: TD-6 — Priority: Medium
  - [ ] Introduce explicit types derived from `combineSearchResultsInputSchema` and `combineSearchResultsResponseSchema`
  - [ ] Replace `any` sorting/access with typed reads (or validate/normalize inputs first)
  - [ ] Keep the implementation small; rely on schema validation + narrow helpers
  - **Done when:** the Biome `noExplicitAny` suppressions for `combineSearchResults` are removed and output validation still passes.

- [ ] AI SDK tool factory typing: remove `(tool as any)` **only if simpler** (Typing) — refs: TD-6, D7 — Priority: Low
  - [ ] Attempt to tie `createAiTool` generics directly to the Zod schemas so `tool()` can infer types
  - [ ] If the refactor increases complexity (more generics / harder call sites), revert and document the cast as deliberate debt
  - **Done when:** either (a) `(tool as any)` is removed without increasing cognitive load, or (b) it is explicitly retained with rationale and a regression test.

- [ ] Standardize env access through validated helpers (Tooling/Safety) — refs: TD-15 — Priority: Medium
  - **Discovery command:** `rg -n -P \"process\\.env\\.(?!NODE_ENV|NEXT_PUBLIC_)\" src`
  - [ ] Migrate the primary candidates from TD-15 to validated env helpers:
    - [ ] `src/lib/memory/mem0-adapter.ts` (`MEM0_API_KEY`)
    - [ ] `src/domain/amadeus/client.ts` (`AMADEUS_ENV`)
    - [ ] `src/config/bot-protection.ts` (`BOTID_ENABLE`)
    - [ ] `src/lib/idempotency/redis.ts` (`IDEMPOTENCY_FAIL_OPEN`)
    - [ ] `src/lib/telemetry/constants.ts` (`TELEMETRY_SILENT`)
    - [ ] `src/lib/http/ip.ts` (`VERCEL`, `TRUST_PROXY`)
  - [ ] Keep explicit, documented exceptions:
    - [ ] env helper modules under `src/lib/env/**`
    - [ ] `process.env.NODE_ENV` / `NEXT_PHASE` / `NEXT_RUNTIME` guards (compile/build/runtime behavior)
  - **Done when:** critical secrets/config are read through validated helpers and remaining direct reads are either (a) in env modules, (b) tests, or (c) documented intentional exceptions.

### 9.6 Tests & Coverage

- [ ] Replace remaining test casts with `unsafeCast<T>()` (Testing) — refs: TD-8 — Priority: Low
  - [ ] Find remaining violations: `rg \"as unknown as\" src | rg -v \"src/test|__tests__\"` (and fix in tests using `unsafeCast<T>()`)
  - [ ] Update at least: `src/app/api/chat/stream/__tests__/route.smoke.test.ts`
  - **Done when:** test-only unsafe cast helper is used consistently (no new `as unknown as` in tests).

- [ ] Add focused tests for chat context compression + tool-call pairing logic (Testing) — refs: TD-9 — Priority: Medium
  - [ ] Identify the smallest pure units inside `src/ai/agents/chat-agent.ts` suitable for unit testing (avoid async Server Component limitations)
  - [ ] Add deterministic unit tests using AI SDK test helpers (MockLanguageModelV3 / tracked mock models) per repo testing standards
  - **Done when:** the highest-complexity logic is covered by fast unit tests and contributes to coverage improvement.

- [ ] Incrementally raise Vitest coverage thresholds (Testing) — refs: TD-9, D8 — Priority: Medium
  - [ ] Consult `docs/development/testing/coverage-milestones.md` and choose the next incremental target
  - [ ] Raise thresholds only after tests are added (avoid “coverage theater”)
  - **Done when:** thresholds are higher than baseline and CI remains green.

### 9.7 Maintainability Refactors

- [ ] Split large Zustand stores into slices per repo standard (Maintainability) — refs: TD-13 — Priority: Medium
  - [ ] Follow `docs/development/standards/standards.md#zustand-stores` and computed middleware guidance
  - [ ] Refactor targets:
    - [ ] `src/stores/budget-store.ts`
    - [ ] `src/stores/search-results-store.ts`
    - [ ] `src/stores/search-filters-store.ts`
  - [ ] Ensure selectors remain exported and no barrel exports are introduced
  - **Done when:** each store is <~300 LOC per slice where feasible and behavior is preserved (tests/TS).

- [ ] Extract large dashboard client components into subcomponents/hooks (Maintainability) — refs: TD-13 — Priority: Medium
  - [ ] Refactor targets:
    - [ ] `src/app/dashboard/search/hotels/hotels-search-client.tsx`
    - [ ] `src/app/dashboard/search/activities/activities-search-client.tsx`
    - [ ] `src/components/features/search/forms/destination-search-form.tsx`
  - [ ] Extract pure helpers (mapping/formatting) to adjacent modules and add unit tests where logic is non-trivial
  - **Done when:** UI modules are smaller, responsibilities are clearer, and tests cover extracted logic.

### 9.8 Docs & Tooling Alignment

- [ ] Run Knip audit and remove unused deps/files (Tooling) — refs: TD-16 — Priority: Medium
  - [ ] Run `pnpm deps:report` and capture output in Section 11
  - [ ] Remove unused deps/files iteratively (run `pnpm deps:audit` after each chunk)
  - **Done when:** Knip reports are clean (or remaining items are documented as deliberate).

### 9.9 Product TODO Decisions

- [ ] Remove “personalized tips” TODO and keep tips explicitly general (Product) — refs: TD-12, D9 — Priority: Low
  - Target file: `src/app/dashboard/search/hotels/hotels-search-client.tsx`
  - [ ] Remove the TODO comment about “personalized tips”
  - [ ] Ensure the card title/description does **not** imply personalization
  - **Done when:** no “future personalization” TODO remains and the UI copy is accurate.

### 9.10 Security Hardening (AI Markdown Rendering)

- [ ] Disable raw HTML in Streamdown defaults for AI-generated content (Security) — refs: TD-17, D12 — Priority: High
  - Target file: `src/components/ai-elements/streamdown-config.ts`
  - [ ] Omit `defaultRehypePlugins.raw` from `streamdownRehypePlugins` so HTML tags are escaped instead of interpreted
  - [ ] Keep KaTeX + harden restrictions (`allowedProtocols: ['http','https','mailto']`, `allowDataImages: false`)
  - [ ] Add targeted tests (Vitest/jsdom) to prevent regressions:
    - [ ] Rendering `<Response>` with HTML tags does not create DOM `<script>` elements and shows escaped text
    - [ ] `javascript:` links are blocked/rewritten per harden configuration
  - [ ] Manual smoke: verify KaTeX, code blocks, and Mermaid still render correctly in chat UI
  - **Done when:** AI markdown no longer interprets raw HTML and link protocols are still restricted.

### 9.B Completed Work (Implemented)

- [x] Capture a Phase 2 baseline run (Tooling) — record outputs in **Section 11** — refs: TD-* (all) — Priority: High
  - [x] Record `git status -sb` (note dirty/untracked; confirm whether `.knip-files.json` exists)
  - [x] Run `pnpm biome:fix`
  - [x] Run `pnpm type-check`
  - [x] Run `pnpm test:affected`
  - [x] Run guardrails:
    - [x] `pnpm boundary:check`
    - [x] `pnpm ai-tools:check`
    - [x] `pnpm check:no-new-domain-infra-imports`
    - [x] `pnpm check:no-new-unknown-casts`
  - [x] If anything fails, append a new checklist item under the relevant section and link it from **Section 11**
  - **Done when:** Section 11 contains a dated baseline snapshot + either (a) all green, or (b) explicit follow-up tasks added.

- [x] Fix React Hook Form + Zod resolver typing in shared hooks (Typing) — refs: TD-6, D4 — Priority: Medium
  - [x] Update `src/hooks/use-zod-form.ts` to remove `schema as any` by making the hook schema-generic and setting RHF generics appropriately
  - [x] Update `src/components/features/search/common/use-search-form.ts` similarly, so feature forms no longer need local casting
  - [x] `rg "zodResolver\\(schema as any\\)" src` returns 0 matches
  - **Done when:** both hooks compile without suppressions and call sites remain ergonomic (no repeated generics everywhere).

- [x] Fix Zod v4 refine option style (`message` → `error`) (Consistency) — refs: TD-7 — Priority: Low
  - [x] Update `src/ai/tools/schemas/google-places.ts` to use `{ error: ... }` per Zod v4 docs (see links in **9.0**)
  - **Done when:** schema matches repo conventions; no runtime behavior change.

- [x] Align AI SDK version references across docs + add drift guard (Docs/Tooling) — refs: TD-10, D5 — Priority: Low
  - [x] Update beta-pinned docs to match reality (or replace with “see `package.json`” references)
  - [x] Replace beta-only doc links with stable `ai-sdk.dev` / `v6.ai-sdk.dev` references where appropriate (see **9.0**)
  - [x] Add a small script to verify docs don’t reintroduce beta pins, and wire it into CI/`pnpm` scripts (`pnpm check:ai-sdk-version-contract`)
  - **Done when:** no project docs reference obsolete beta pins, and an automated check prevents drift.

- [x] Resolve `TODO(ARCH-001/002)` script debt (Docs/Tooling) — refs: TD-11 — Priority: Low
  - [x] Remove TODO markers while preserving the guardrail allowlist mechanism (D11)
  - [x] `scripts/check-boundaries.mjs`: replace `TODO(ARCH-001)` with non-TODO allowlist documentation and require explicit justification
  - [x] `scripts/check-ai-tools.mjs`: replace `TODO(ARCH-002)` with non-TODO allowlist documentation and require explicit justification
  - **Done when:** no `TODO(ARCH-*)` remains, and any future allowlist entry requires explicit justification + tracking.

- [x] Implement trip collaboration page end-to-end (Product) — refs: TD-12, D10 — Priority: Medium
  - [x] Replace stubbed collaborator/invite state with real collaborator CRUD (invite/update role/remove/leave) backed by `/api/trips/[id]/collaborators*` + Supabase RLS
  - [x] Add real-time activity feed using private Realtime Broadcast channel `trip:{tripId}` and wire it into edits + collaborator actions
  - [x] Gate live trip editing by role (owner/admin/editor can edit; viewer is read-only) while keeping server-side enforcement via RLS
  - [x] Add schemas/hooks/tests for collaborator flows and ensure trip list caches invalidate for all trip members
  - **Done when:** collaboration page has no fake actions/stub state and is fully functional end-to-end.

## 10. Risks, Trade-offs, and Notes

- **Boundary refactors are high-risk by nature.** Decoupling domain services from infra will touch route handlers, tests, and potentially telemetry/caching behavior. Mitigate by:
  - making changes incrementally,
  - adding tests around the “contract” boundary,
  - running `pnpm test:affected` frequently.
- **Type “fixes” can backfire** if they rely on brittle assertions. Prefer small, well-tested typed wrappers.
- **Markdown rendering security hardening:** disabling `rehype-raw` for AI output (TD-17/D12) may change how literal `<tags>` appear in model output (they will be escaped). Mitigate with a small jsdom test + a quick manual chat smoke.
- **Performance:** switching from singletons to per-request factories is typically fine, but avoid per-request heavy instantiation of clients that can be safely reused (e.g., Upstash clients) — follow existing patterns and keep construction lightweight.
- **Dirty worktree:** because the repo is currently dirty, Phase 2 should be careful not to trample unrelated ongoing work. If Phase 2 is meant to land as a single PR, consider starting from a clean branch to avoid mixing unrelated local changes. (UNVERIFIED: intent of current local diffs.)

## 11. Final Status

### Phase 1: Complete (2025-12-26)

- All technical debt items catalogued and analyzed.
- Decisions finalized with evidence-backed scoring where applicable.
- Baseline established (guardrails passing).

### Phase 2: Outstanding

- 10 major work sections remain; see Section **9.A** for the detailed checklist.

> This section is updated continuously during **Phase 2** to record the baseline and final verification runs.

- All planned tasks completed: **No** — see remaining items in **9.A**.
- All technical debt items addressed: **No** — TD-1/TD-2/TD-3/TD-4/TD-5/TD-8/TD-9/TD-13/TD-14/TD-15/TD-16/TD-17 remain.

### 2025-12-27 Baseline Snapshot (Phase 2)

- [x] `git status -sb` recorded (worktree is dirty; untracked trip collaboration hooks/components present; no `.knip-files.json` observed).
- [x] `pnpm biome:fix` ✅
- [x] `pnpm type-check` ✅
- [x] `pnpm test:affected` ✅
- [x] Guardrails:
  - [x] `pnpm boundary:check` ✅
  - [x] `pnpm ai-tools:check` ✅
  - [x] `pnpm check:no-new-domain-infra-imports` ✅
  - [x] `pnpm check:no-new-unknown-casts` ✅
  - [x] `pnpm check:ai-sdk-version-contract` ✅

- Residual known issues or deliberate debts: tracked as outstanding checklist items in **9.A**.
