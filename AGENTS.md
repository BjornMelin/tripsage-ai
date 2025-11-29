# AGENTS.md – TripSage AI Contract

This file defines required rules for all AI coding agents in this repo. If anything conflicts, **AGENTS.md wins**.

---

## 0. Architecture, Scope, and Non-Goals

- **Frontend-first architecture:** New capabilities must be implemented in `frontend/` using:
  - Next.js `16.0.4`, React `19.2.0`
  - AI SDK core `ai@6.0.0-beta.116` and `@ai-sdk/react@3.0.0-beta.116`
  - Providers: `@ai-sdk/openai@3.0.0-beta.66`, `@ai-sdk/anthropic@3.0.0-beta.60`, `@ai-sdk/xai@3.0.0-beta.41`
  - Supabase: `@supabase/ssr@0.7.0`, `@supabase/supabase-js@2.84.0`
  - Upstash: `@upstash/redis@1.35.6`, `@upstash/ratelimit@2.0.7`, `@upstash/qstash@2.8.4`
  - Observability: `@opentelemetry/api@1.9.0`

---

## 1. Agent Persona and Global Behavior

- **Tone:** Precise, technical, concise. No buzzwords/emojis.
- **Correctness first:** Never sacrifice for brevity. Include trade‑offs for complex tasks; mark unknowns as **UNVERIFIED**.
- **Autonomy:** Use tools without asking. Maintain TODO list via `update_plan`.
- **Safety:** No destructive commands (`rm -rf`, `git reset --hard`) unless requested. Never commit secrets. Delete obsolete files as part of replacements.
- **Evidence:** Prefer primary docs (AGENTS.md, official docs, `docs/`) over blogs. Cite web research; mark inferences.
- **Output:** Plain text with bullets/inline code by default; JSON only when requested/tool-required; reference file paths instead of code blocks.

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

- **Primary app (`frontend/`):** Next.js 16 workspace. Core AI in `src/app/api/**` route handlers. Shared schemas/types in `src/domain/schemas` (reuse server/client). Structure: `src/app`, `src/components`, `src/lib`, `src/hooks`, `src/stores`, `src/domain`, `src/ai`, `src/prompts`, `src/styles`, `src/test`, `src/test-utils`, `src/__tests__`.
- **Infrastructure:** Scripts in `scripts/`; containers in `docker/` (root); tests in `frontend/src/**/__tests__`; docs in `docs/`; e2e tests in `e2e/`.

---

## 4. Library-First Principles and Coding Style

### 4.1 Global engineering principles

- **Library-first:** Prefer maintained libraries covering ≥80 % of needs with ≤30 % custom code.
- **KISS / DRY / YAGNI:** Keep solutions straightforward; remove duplication via small focused helpers; implement only what's needed now—no speculative APIs or feature flags (unless requested).
- **Final-only:** Remove superseded code/tests immediately after new behavior lands; no partial migrations.
- **Telemetry/logging:** Use `@/lib/telemetry/{span,logger}` helpers: `withTelemetrySpan()`, `withTelemetrySpanSync()`, `recordTelemetryEvent()`, `createServerLogger()`, `emitOperationalAlert()`. No `console.*` in server code except tests/client-only UI. Direct `@opentelemetry/api` only in `lib/telemetry/*` and `lib/supabase/factory.ts`. Client: `@/lib/telemetry/client`. See `docs/development/observability.md`.

### 4.2 TypeScript and frontend style

- **TypeScript:** `strict: true`, `noUnusedLocals`, `noFallthroughCasesInSwitch`. Avoid `any`; use precise unions/generics. Handle `null`/`undefined` explicitly.
- **Biome:** `pnpm format:biome`, `pnpm biome:check` (must pass), `pnpm biome:fix`. Do **not** edit `frontend/biome.json`; fix code instead.
- **File structure:**
  - Source (`.ts`, `.tsx`): Optional `@fileoverview`, blank line, `"use client"` (if needed), blank line, imports, implementation.
  - Test (`*.test.ts`, `*.spec.ts`): No `@fileoverview`. Use `@vitest-environment` only when overriding default.
- **JSDoc:** Use `/** ... */` for public APIs; `//` for notes. Document top‑level exports and non‑obvious functions. Avoid repeating types or TS‑duplicated tags.
- **IDs/timestamps:** Use `@/lib/security/random` (`secureUuid`, `secureId`, `nowIso`). Never `Math.random` or `crypto.randomUUID` directly.
- **Imports/exports:** Import directly from slice modules (e.g., `@/stores/auth/auth-core`, not `@/stores`). No barrel files or `export *` for stores/selectors.
- **Path aliases:**
  - `@schemas/*` → `./src/domain/schemas/*` (Zod/domain schemas)
  - `@domain/*` → `./src/domain/*` (accommodations, amadeus, types)
  - `@ai/*` → `./src/ai/*` (AI SDK tooling, models)
  - `@/*` → `./src/*` (generic: lib, components, stores)
  - **Disallowed:** Never use `@/domain/*`, `@/ai/*`, or `@/domain/schemas/*`; use `@domain/*`, `@ai/*`, `@schemas/*`.
  - **Relative imports:** Within feature slices (e.g., `src/domain/amadeus/*`), prefer relative; cross-boundary, use aliases.

### 4.3 State management (frontend)

- Use `zustand`, `@tanstack/react-query`, Supabase Realtime. No new state/websocket libraries without approval.

### 4.4 Zod v4 schemas

- **ONLY** use Zod v4 APIs; no Zod 3 deprecated APIs.
- **Error handling:** Use unified `error` option (`z.string().min(5, { error: "Too short" })`); avoid `message`, `invalid_type_error`, `required_error`, `errorMap`.
- **String helpers:** Use top‑level (`z.email()`, `z.uuid()`, `z.url()`, `z.ipv4()`, `z.ipv6()`, `z.base64()`, `z.base64url()`); avoid method style.
- **Enums:** Use `z.enum(MyEnum)` for TS enums; not `z.nativeEnum()`.
- **Objects/records:** Prefer `z.strictObject(...)`, `z.looseObject(...)`, `z.record(keySchema, valueSchema)`, `z.partialRecord(z.enum([...]), valueSchema)`. Avoid `z.record(valueSchema)`, `z.deepPartial()`, `.merge()`.
- **Numbers:** Use `z.number().int()` for integers.
- **Defaults/transforms:** Use `.default()` for output defaults; `.prefault()` when default must be parsed.
- **Functions:** Prefer `z.function({ input: [...], output }).implement(...)` or `.implementAsync(...)`; avoid `z.promise()` and `.args().returns()`.

### 4.5 Schema organization

- **Single file per domain:** Core business + tool input schemas together (e.g., `calendar.ts`, `memory.ts`).
- **Import path:** `@schemas/domain-name` (no `.schema` suffix).
- **Section markers:** Use `// ===== CORE SCHEMAS =====` and `// ===== TOOL INPUT SCHEMAS =====` to separate concerns.
- **No barrel exports:** Import directly from domain modules; `lib/schemas/index.ts` removed in favor of aliases.
- **Details:** See `docs/development/zod-schema-guide.md`.

---

## 5. Frontend Architecture and Patterns

### 5.1 Next.js route handlers and adapters

- Route Handlers: `frontend/src/app/api/**/route.ts` for all server‑side HTTP entrypoints.
- Adapters: parse `NextRequest`, construct SSR clients/ratelimiters/config **inside** handler (no module‑scope), delegate to DI handlers (`_handler.ts`).
- DI handlers: pure functions; accept `supabase`, `resolveProvider`, `limit`, `stream`, `clock`, `logger`, `config`. No `process.env` or global state.

### 5.2 AI SDK v6 usage

- Use AI SDK v6 primitives only; no custom streaming/tool-calling.
- Chat/streaming: `convertToModelMessages()` → `streamText(tools, outputs)` → `result.toUIMessageStreamResponse()`.
- Structured JSON: use `generateObject` or `streamObject` with Zod schemas from `@schemas/*`.

### 5.3 Models and providers

- **Vercel AI Gateway (primary):**
  - Configure via `createGateway({ baseURL: "https://ai-gateway.vercel.sh/v1", apiKey: process.env.AI_GATEWAY_API_KEY })`.
- **BYOK registry (alternative):**
  - Source: `frontend/src/ai/models/registry.ts`; resolves user keys server‑side.
  - Supported: `openai`, `openrouter`, `anthropic`, `xai`.
- **BYOK routes:**
  - Must import `"server-only"`.
  - Dynamic by default (Cache Components); never add `'use cache'` directives.
- **Per route:** Use either Gateway or BYOK; do **not** mix.

### 5.4 Caching, Supabase SSR, and performance

- **Caching:** `cacheComponents: true` enabled. Cache directives (`'use cache'` / `'use cache: private'`) **cannot** access `cookies()` or `headers()`; use only for public/non-auth routes. Auth/BYOK/settings routes: dynamic by default (never cache). See ADR-0024.
- **Supabase SSR:** Use `createServerSupabase()` from `frontend/src/lib/supabase/server.ts` (server-only); auto-dynamic. Never access cookies in Client Components.
- **Performance:** `next/font`, `next/image` (`sizes`/`priority`), Server Components, Suspense, `useActionState`/`useOptimistic`.

### 5.5 Rate limiting and ephemeral state

- **Rate limiting:** Use `@upstash/ratelimit` + `@upstash/redis`; initialize inside handlers (not module-scope) via `Redis.fromEnv()` and `Ratelimit` per request.
- **Background tasks:** Use Upstash QStash with idempotent, stateless handlers.

### 5.6 Agent configuration

- **Agent config backend (SPEC-0029 / ADR-0052):** Routes: `/api/config/agents/:agentType` (GET/PUT), `/api/config/agents/:agentType/versions` (GET), `/api/config/agents/:agentType/rollback/:versionId` (POST). Schemas in `@schemas/configuration`; single source of truth: `frontend/src/lib/agents/config-resolver.ts`.

---

## 6. Testing and Quality Gates

### 6.1 Frontend testing

- **Framework & locations:** Vitest + jsdom, Playwright (e2e). Tests: `frontend/src/**/__tests__`; mocks: `frontend/src/test`; pattern: `**/*.{test,spec}.ts?(x)`.
- **Environment declarations (MANDATORY):** Add `/** @vitest-environment jsdom */` (first line) only for `@testing-library/react`, DOM APIs, or browser hooks. Skip node-only code. Prevents misclassification.
- **Commands:** `pnpm test:run`, `pnpm test` (watch), `pnpm test:e2e`; single file: `--project=<name>`.
- **Coverage:** Meet `frontend/vitest.config.ts` thresholds; update tests with code changes.

### 6.2 Quality gates

- Run `pnpm biome:check`, `pnpm biome:fix`, `pnpm type-check`, and relevant `pnpm test*` on changed areas only.

### Upstash testing (must follow)

- **Mocking:** `setupUpstashMocks()` (`frontend/src/test/setup/upstash.ts`) with `__reset()` in `beforeEach`. MSW handlers at `frontend/src/test/msw/handlers/upstash.ts`; no ad-hoc mocks.
- **Emulator (optional):** `UPSTASH_USE_EMULATOR=1` + `UPSTASH_EMULATOR_URL`, `UPSTASH_QSTASH_DEV_URL`; see `frontend/src/test/upstash/emulator.ts`.
- **Commands:** `pnpm -C frontend test:upstash:{unit,int,smoke}`. Live smoke requires `UPSTASH_SMOKE=1` + valid creds; contracts in `frontend/src/__tests__/contracts/`.

---

## 7. Security and Secrets

- Never commit/log secrets; use `.env` and env vaults.
- Keep provider keys server‑side only; never expose to client.
- Do not publicly cache user‑specific or cookie-dependent data.
- Use maintained security libraries; no custom crypto/auth.

---

## 8. Git, Commits, and PRs

- Use Conventional Commit messages with scopes: i.e. `feat(scope): ...`
- Small commits and focused; group related changes.

---

## 9. Anti‑Patterns and Hard "Don'ts"

- **Prohibitions:** No custom streaming/tool-calling, schema duplication, module-scope state in route handlers, or config changes without approval. Use AI SDK v6; centralize schemas in `frontend/src/schemas`.
