# AGENTS.md – TripSage AI Contract

This file defines required rules for all AI coding agents in this repo. If anything conflicts, **AGENTS.md wins**.

---

## 0. Architecture, Scope, and Non‑Goals

- **Frontend‑first architecture:** New capabilities must be implemented in `frontend/` using:
  - Next.js `16.0.1`, React `19.2.0`
  - AI SDK core `ai@6.0.0-beta.99` and `@ai-sdk/react@3.0.0-beta.99`
  - Providers: `@ai-sdk/openai`, `@ai-sdk/anthropic`, `@ai-sdk/xai`, `@ai-sdk/google`
  - Supabase: `@supabase/ssr@0.7.0`, `@supabase/supabase-js@2.76.1`
  - Upstash: `@upstash/redis@1.35.6`, `@upstash/ratelimit@2.0.7`, `@upstash/qstash@2.8.4`
  - Observability: `@opentelemetry/api`

---

## 1. Agent Persona and Global Behavior

- **Tone:** Precise, technical, concise. Avoid hype; prefer bullets. **NEVER use buzzwords or emojis**.
- **Correctness first:** Never sacrifice correctness for brevity. For complex tasks, include trade‑offs and reasoning. Mark unknowns as **UNVERIFIED**.
- **Autonomy:** Use tools without asking permission. Maintain TODO list via `update_plan` for multi‑step work.
- **Safety:** No destructive commands (`rm -rf`, `git reset --hard`) unless explicitly requested. Never commit/log secrets. OK to delete obsolete files as part of replacements.
- **Evidence:** Prefer primary docs (this AGENTS.md, official docs, `docs/`) over blogs. Cite sources in web research; mark inferences.
- **Output defaults:** Plain text with bullets/inline code by default; JSON/structured outputs only when requested or tool-required; reference file paths instead of dumping code blocks.

---

## 2. Planning, Tools, and Research

### 2.1 Planning and investigation

- For any non‑trivial or multi‑step change, use `zen.planner` plus `update_plan` (with exactly one `in_progress` step).
- For non‑obvious design trade‑offs, use `zen.consensus` and apply the weighted decision framework:
  - **Solution Leverage (35%)**
  - **Application Value (30%)**
  - **Maintenance & Cognitive Load (25%)**
  - **Architectural Adaptability (10%)**

### 2.2 Search and documentation tools

- **Code and API questions:** Use `context7`(resolve-library-id → get-library-docs),then `exa.get_code_context_exa`.
- **Research/web search:** Use `exa.web_search_exa`.
- **Scraping/Crawling:** Use `exa.crawling_exa`.

---

## 3. Project Layout and Responsibilities

- **Primary app (`frontend/`):**
  - Next.js 16 workspace with `src/app`, `components`, `lib`, `hooks`, `contexts`, `stores`, `types`, `schemas`.
  - Core AI behavior lives in route handlers under `frontend/src/app/api/**`.
  - Shared types and Zod schemas live in `frontend/src/schemas`; reuse them across server/client.
- **Infrastructure and automation:**
  - Scripts: `scripts/` for verification and utilities.
  - Containers: `docker/` and `docker-compose.yml`.
  - Tests: legacy backend tests in `tests/`, frontend tests under `frontend/src/**/__tests__`.

---

## 4. Library‑First Principles and Coding Style

### 4.1 Global engineering principles

- **Library‑first:** Prefer maintained libraries covering ≥80 % of needs with ≤30 % custom code.
- **KISS / DRY / YAGNI:** Keep solutions straightforward; remove duplication via small focused helpers; implement only what's needed now—no speculative APIs or feature flags (unless requested).
- **Final‑only:** Remove superseded code/tests immediately after new behavior lands; no partial migrations.
- **Telemetry/logging:** Server code must use helpers from `@/lib/telemetry/span` (server-only) and `@/lib/telemetry/logger`: `withTelemetrySpan()` (async), `withTelemetrySpanSync()` (sync), `recordTelemetryEvent()` (events), `createServerLogger()` (structured logs), `emitOperationalAlert()` (critical alerts). Never use `console.*` in server modules except tests, client-only UI, or `lib/telemetry/alerts.ts`. Direct `@opentelemetry/api` usage allowed only in `lib/telemetry/*` and `lib/supabase/factory.ts`. Client components should use `@/lib/telemetry/client` for client-side telemetry initialization. See `docs/developers/observability.md`.

### 4.2 TypeScript and frontend style

- **TypeScript:** `strict: true`, `noUnusedLocals`, `noFallthroughCasesInSwitch`. Avoid `any`; use precise unions/generics. Handle `null`/`undefined` explicitly.
- **Biome:** `pnpm format:biome`, `pnpm biome:check` (must pass), `pnpm biome:fix`. Do **not** edit `frontend/biome.json`; fix code instead.
- **File structure:**
  - Source (`.ts`, `.tsx`): Optional `@fileoverview`, blank line, `"use client"` (if needed), blank line, imports, implementation.
  - Test (`*.test.ts`, `*.spec.ts`): No `@fileoverview`. Use `@vitest-environment` only when overriding default.
- **JSDoc:** Use `/** ... */` for public APIs; `//` for notes. Document top‑level exports and non‑obvious functions. Avoid repeating types or TS‑duplicated tags (`@private`, `@implements`).
- **IDs/timestamps:** Use `@/lib/security/random` (`secureUuid`, `secureId`, `nowIso`). Never `Math.random` or `crypto.randomUUID` directly.
- **Imports/exports:** Import directly from slice modules (e.g., `@/stores/auth/auth-core`, not `@/stores`). No barrel files or `export *` for stores/selectors. Exception: `lib/schemas/index.ts`.
- **Path aliases:** Use semantic aliases for architectural boundaries:
  - `@schemas/*` → `./src/domain/schemas/*` (canonical for all Zod/domain schemas)
  - `@domain/*` → `./src/domain/*` (domain logic: accommodations, expedia, types)
  - `@ai/*` → `./src/ai/*` (AI SDK tooling, models, helpers)
  - `@/*` → `./src/*` (generic src-root: `@/lib/*`, `@/components/*`, `@/stores/*`, etc.)
  - **Disallowed patterns:** Never use `@/domain/*`, `@/ai/*`, or `@/domain/schemas/*`; use `@domain/*`, `@ai/*`, and `@schemas/*` respectively.
  - **Relative imports:** Prefer relative imports (`./client-types`, `../utils`) within local feature slices (e.g., inside `src/domain/expedia/*` or `src/ai/tools/server/*`). Use aliases when crossing architectural boundaries.

### 4.3 State management (frontend)

- **Libraries:** `zustand` (client UI state), `@tanstack/react-query` (server state), Supabase Realtime (real‑time collaboration).
- **Constraints:** No new state management or websocket libraries without approval.

### 4.4 Zod v4 schemas

- Use Zod v4 APIs as canonical; no Zod 3‑style helpers in new code.
- **Error handling:** Prefer unified `error` option (`z.string().min(5, { error: "Too short" })`). Avoid `message`, `invalid_type_error`, `required_error`, global `errorMap`.
- **String helpers:** Use top‑level helpers (`z.email()`, `z.uuid()`, `z.url()`, `z.ipv4()`, `z.ipv6()`, `z.base64()`, `z.base64url()`). Avoid method style (`z.string().email()`, `.uuid()`).
- **Enums:** Use `z.enum(MyEnum)` for TS enums. Do not use `z.nativeEnum(MyEnum)`.
- **Objects and records:** Prefer `z.strictObject(...)`, `z.looseObject(...)`, `z.record(keySchema, valueSchema)`, `z.partialRecord(z.enum([...]), valueSchema)`. Avoid `z.record(valueSchema)`, `z.deepPartial()`, `.merge()` when `.extend()` or object spread suffices.
- **Numbers:** Use `z.number().int()` for integers; avoid unsafe ranges.
- **Defaults and transforms:** `.default()` for output defaults; `.prefault()` when default must be parsed by schema.
- **Functions and promises:** Prefer `z.function({ input: [...], output }).implement(...)` / `.implementAsync(...)`. Avoid `z.promise()` and `z.function().args().returns()` in new code.

### 4.5 Schema organization

- **Consolidated structure:** Each domain has a single schema file containing both core business schemas and tool input validation schemas.
- **File naming:** Use domain names (e.g., `calendar.ts`, `memory.ts`) without `.schema` suffix.
- **Section separation:** Use clear comments (`// ===== CORE SCHEMAS =====`, `// ===== TOOL INPUT SCHEMAS =====`) to separate concerns within files.
- **Import path:** Always use `@schemas/domain-name` (no `.schema` suffix).
- **No barrel file:** Import schemas directly from their domain module; `lib/schemas/index.ts` has been removed in favor of module-based aliases.
- **Reference:** See `docs/developers/zod-schema-guide.md` for comprehensive Zod schema standards and patterns.

---

## 5. Frontend Architecture and Patterns

### 5.1 Next.js route handlers and adapters

- Route Handlers in `frontend/src/app/api/**/route.ts` for all server‑side HTTP entrypoints.
- Adapters: parse `NextRequest`, construct SSR clients/ratelimiters/config **inside** handler (no module‑scope), delegate to DI handlers (`_handler.ts` or `_handlers.ts`).
- DI handlers: pure functions accepting collaborators (`supabase`, `resolveProvider`, `limit`, `stream`, `clock`, `logger`, `config`). No `process.env` reads or global state.

### 5.2 AI SDK v6 usage

- Use AI SDK v6 primitives; **NO** custom streaming or tool‑calling frameworks.
- Typical pattern for chat/streaming:
  - Convert UI messages with `convertToModelMessages(messages)`.
  - Use `streamText` with tools and/or structured outputs (`Output` or Zod schemas).
  - Return `result.toUIMessageStreamResponse()` from route handlers.
- For structured JSON responses without streaming, use `generateObject` or `streamObject` with shared Zod schemas from `frontend/src/schemas`.

### 5.3 Models and providers

- **Vercel AI Gateway (primary):**
  - Configure via `createGateway({ baseURL: "https://ai-gateway.vercel.sh/v1", apiKey: process.env.AI_GATEWAY_API_KEY })`.
- **BYOK registry (alternative):**
  - Source: `frontend/src/lib/providers/registry.ts`; resolves user keys server‑side.
  - Supported: `openai`, `openrouter`, `anthropic`, `xai`.
- **BYOK routes:**
  - Must import `"server-only"`.
  - Dynamic by default (Cache Components); never add `'use cache'` directives.
- **Per route:** Use either Gateway or BYOK; do **not** mix.

### 5.4 Caching, Supabase SSR, and performance

- Caching:
  - Next.js `cacheComponents: true` is enabled.
  - Use `'use cache'` for cacheable, public data; `'use cache: private'` for user‑specific data.
  - **Security-sensitive routes (BYOK, user settings, auth-dependent):** Dynamic by default; never export `dynamic`/`revalidate` or use `'use cache'` directives. Ensure `withApiGuards({ auth: true })` or `cookies()`/`headers()` access to guarantee dynamic execution. Add comments referencing ADR-0024.
- **Supabase SSR:** Use server client factories (`frontend/src/lib/supabase/server.ts`); never access Supabase cookies in client components.
- **Performance:** Use `next/font`, `next/image` with `sizes`/`priority`. Prefer Server Components; use Client Components only for interactivity. Apply Suspense for slow UI and `useActionState`/`useOptimistic` for forms.

### 5.5 Rate limiting and ephemeral state

- **Rate limiting:** Use `@upstash/ratelimit` + `@upstash/redis`. Initialize both inside route handlers (not module-scope); call `Redis.fromEnv()` and `Ratelimit` per request.
- **Background tasks:** Use Upstash QStash; ensure handlers are idempotent and stateless.

---

## 6. Testing and Quality Gates

### 6.1 Frontend testing

- **Framework & locations:** Vitest (unit/integration) with jsdom; Playwright for e2e. Tests under `frontend/src/**/__tests__`, helpers/mocks under `frontend/src/test`, patterns `**/*.{test,spec}.ts?(x)`.
- **Environment declarations (MANDATORY):**
  - **MUST add** `/** @vitest-environment jsdom */` as first line if file uses `@testing-library/react`, DOM APIs (`document`, `window`, `HTMLElement`), or browser-dependent hooks.
  - **Do NOT add** for node-only code: pure functions, utilities, API route handlers without DOM, or code already assigned by `vitest.config.ts` project rules.
  - **Why:** Explicit declaration prevents misclassification even when config sets defaults.
- **Commands:**
  - `pnpm test:run` – full suite; `pnpm test` – watch/dev; `pnpm test:e2e` – e2e only.
  - **Single file:** Always use `--project=<name>` to limit scope (omitting runs all matching projects).
- **Coverage:** Treat `frontend/vitest.config.ts` thresholds as minimum. Update tests for code you change.

### 6.2 Quality gates (when touching code)

- **Frontend:** `pnpm biome:check`, `pnpm biome:fix`, `pnpm type-check`, relevant `pnpm test*` for changed areas.
- **Scope:** Run only on changed files/areas; full‑repo gates only when necessary.

---

## 7. Security and Secrets

- Never commit secrets; use `.env` (from `.env.example`) and env vaults. Do not log/echo secrets in code, docs, or responses.
- Keep provider keys server‑side: Vercel AI Gateway and BYOK providers resolve on server only; never expose to client.
- Do not publicly cache user‑specific or cookie-dependent responses.
- Use maintained security libraries; avoid custom crypto/auth.

---

## 8. Git, Commits, and PRs

- Use Conventional Commit messages with scopes: i.e. `feat(scope): ...`
- Small commits and focused; group related changes.

---

## 9. Anti‑Patterns and Hard "Don'ts"

- **Prohibitions:** No custom streaming/tool-calling (use AI SDK v6), schema duplication (centralize in `frontend/src/schemas`), module-scope state in route handlers, or Biome/TypeScript/test config changes without approval.

## 10. Legacy Python Backend

The `tripsage/` and `tripsage_core/` directories are **removal-only**. All new capabilities go in the Next.js frontend.

- **Prohibitions:** No new endpoints, services, features, dependencies, models, or patterns.
- **When touching:** Migrate to frontend; delete superseded Python code/tests immediately after validation.
- **Style:** Preserve existing conventions (type hints, Google docstrings, async I/O). Derive exceptions from core base classes.
- **Quality gates:** `ruff format .`, `ruff check . --fix`, `uv run pyright`, `uv run pylint`, `uv run pytest` on changed files only.
