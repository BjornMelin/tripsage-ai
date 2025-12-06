# AGENTS.md – TripSage AI Contract

This file defines required rules for all AI coding agents in this repo. If anything conflicts, **AGENTS.md wins**.

---

## 0. Architecture and Stack

- **Frontend-first:** All features in `frontend/`. Next.js 16, React 19, TypeScript 5.9.
- **AI SDK v6 (exact versions):** `ai@6.0.0-beta.127`, `@ai-sdk/react@3.0.0-beta.127`, `@ai-sdk/openai@3.0.0-beta.75`, `@ai-sdk/anthropic@3.0.0-beta.70`, `@ai-sdk/xai@3.0.0-beta.48`. Use these when researching.
- **Data/State:** Zod v4, Zustand v5, React Query v5, React Hook Form.
- **Backend:** Supabase SSR, Upstash (Redis/Ratelimit/QStash), OpenTelemetry.
- **UI:** Radix UI primitives, Tailwind CSS + CVA + clsx, Lucide icons.
- **External APIs:** Amadeus (travel), Stripe (payments), Resend (email).

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
- For design trade‑offs, use `zen.consensus` with weights: Solution Leverage 35%, Application Value 30%, Maintenance 25%, Adaptability 10%.

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
- **Telemetry/logging:** Use `@/lib/telemetry/{span,logger}` helpers: `withTelemetrySpan()`, `withTelemetrySpanSync()`, `recordTelemetryEvent()`, `createServerLogger()`, `emitOperationalAlert()`. Direct `@opentelemetry/api` only in `lib/telemetry/*` and `lib/supabase/factory.ts`. Client: `@/lib/telemetry/client`. See `docs/development/observability.md`.
  - **Server code:** No `console.*` except test files and telemetry infra.
  - **Client-only UI (`"use client"` modules):** Dev-only `console.*` is allowed when guarded by `process.env.NODE_ENV === 'development'`. Bundlers eliminate these calls in prod builds.
  - **Zustand stores:** Use `createStoreLogger` from `@/lib/telemetry/store-logger` for error tracking via OTEL spans.

### 4.2 TypeScript and frontend style

- **TypeScript:** `strict: true`, `noUnusedLocals`, `noFallthroughCasesInSwitch`. Avoid `any`; use precise unions/generics. Handle `null`/`undefined` explicitly.
- **Biome:** `pnpm format:biome`, `pnpm biome:check` (must pass), `pnpm biome:fix`. Do **not** edit `frontend/biome.json`; fix code instead.
- **File structure:**
  - Source (`.ts`, `.tsx`): Optional `@fileoverview`, blank line, `"use client"` (if needed), blank line, imports, implementation.
  - Test (`*.test.ts`, `*.spec.ts`): No `@fileoverview`. Use `@vitest-environment` only when overriding default.
- **JSDoc:** Use `/** ... */` for public APIs; `//` for notes. Document top‑level exports and non‑obvious functions. Avoid repeating types or TS‑duplicated tags.
- **IDs/timestamps:** Use `@/lib/security/random` (`secureUuid`, `secureId`, `nowIso`). Never `Math.random` or `crypto.randomUUID` directly.
- **Imports/exports:** Import from slice modules directly (e.g., `@/stores/auth/auth-core`). No barrel files or `export *`.
  - **Path aliases:** `@schemas/*` (Zod), `@domain/*`, `@ai/*`, `@/*` (generic). **Disallowed:** `@/domain/*`, `@/ai/*`, `@/domain/schemas/*`—use short forms.
  - **Relative imports:** Within feature slices prefer relative; cross-boundary use aliases.
  - **Icons:** `lucide-react` `*Icon` suffixed names (e.g., `AlertTriangleIcon`).

### 4.3 State management (frontend)

- **Libraries:** Use `zustand`, `@tanstack/react-query`, Supabase Realtime. No new state/websocket libs without approval.
- **Store organization:** Small stores (<300 LOC): single file. Large stores: slice composition in `stores/<feature>/*` with unified `index.ts`.
- **Middleware order:** `devtools` → `persist` → `withComputed` → store creator. Computed middleware innermost.
- **Computed properties:** Use `withComputed` from `@/stores/middleware/computed` for aggregations, counts, validation flags. Keep compute functions O(1) or O(n). Never use for simple access (use selectors), async ops, or React context-dependent values.
- **Imports:** See 4.2 path aliases; no barrel files.
- **Logging:** `createStoreLogger` for errors; see 4.1 for telemetry rules.
- **Selectors:** Export named selectors: `export const useSearchType = () => useStore(s => s.type);`
- **Details:** See `docs/development/standards.md#zustand-stores` and `docs/development/zustand-computed-middleware.md`.

### 4.4 Zod v4 schemas

- **ONLY** use Zod v4 APIs; no Zod 3 deprecated APIs.
- **Error handling:** Use unified `error` option (`z.string().min(5, { error: "Too short" })`); avoid `message`, `invalid_type_error`, `required_error`, `errorMap`.
- **String helpers:** Use top‑level (`z.email()`, `z.uuid()`, `z.url()`, `z.ipv4()`, `z.ipv6()`, `z.base64()`, `z.base64url()`); avoid method style.
- **Enums:** Use `z.enum(MyEnum)` for TS enums; not `z.nativeEnum()`.
- **Objects/records:** Prefer `z.strictObject(...)`, `z.looseObject(...)`, `z.record(keySchema, valueSchema)`, `z.partialRecord(z.enum([...]), valueSchema)`. Avoid `z.record(valueSchema)`, `z.deepPartial()`, `.merge()`.
- **Numbers:** Use `z.number().int()` for integers.
- **Defaults/transforms:** Use `.default()` for output defaults; `.prefault()` when default must be parsed.
- **Functions:** Prefer `z.function({ input: [...], output }).implement(...)` or `.implementAsync(...)`; avoid `z.promise()` and `.args().returns()`.
- **Cross-field:** `.refine()` with `path`: `.refine(d => d.end > d.start, { error: "...", path: ["end"] })`.

### 4.5 Schema organization

- **Single file per domain:** Core business + tool input schemas together (e.g., `calendar.ts`, `memory.ts`).
- **Import path:** `@schemas/domain-name`; see 4.2 for aliases.
- **Section markers:** `// ===== CORE SCHEMAS =====`, `// ===== FORM SCHEMAS =====`, `// ===== TOOL INPUT SCHEMAS =====`.
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

- **Vercel AI Gateway (primary):** `createGateway()` with `AI_GATEWAY_API_KEY`.
- **BYOK registry (alternative):** `frontend/src/ai/models/registry.ts`; supports `openai`, `openrouter`, `anthropic`, `xai`.
- **BYOK routes:** Must import `"server-only"`; dynamic by default (never `'use cache'`).
- **Per route:** Use Gateway OR BYOK; never mix.

### 5.4 Caching, Supabase SSR, and performance

- **Caching:** `cacheComponents: true` enabled. Directives (`'use cache'`/`'use cache: private'`) cannot access `cookies()`/`headers()`; public routes only. Auth/BYOK: dynamic. See ADR-0024.
- **Supabase SSR:** `createServerSupabase()` (server-only, auto-dynamic). Never access cookies in Client Components.
- **Performance:** `next/font`, `next/image`, Server Components, Suspense, `useActionState`/`useOptimistic`.

### 5.5 Rate limiting and ephemeral state

- **Rate limiting:** Use `@upstash/ratelimit` + `@upstash/redis`; initialize inside handlers (not module-scope) via `Redis.fromEnv()` and `Ratelimit` per request.
- **Background tasks:** Use Upstash QStash with idempotent, stateless handlers.

### 5.6 Agent configuration

- **Routes (SPEC-0029/ADR-0052):** `/api/config/agents/:agentType` (GET/PUT), versions, rollback. Source: `frontend/src/lib/agents/config-resolver.ts`.

### 5.7 Forms and Server Actions

- **Client forms:** `useZodForm` (`@/hooks/use-zod-form`), `useSearchForm`, `useZodFormWizard`. Components: `Form`, `FormField`, `FormControl`, `FormMessage` from `@/components/ui/form`. Mode: `onChange`; `AbortController` for async cleanup.
- **Server actions:** `"use server"` + `"server-only"` import; Zod validation; `createServerSupabase()`. Location: `src/app/(route)/actions.ts` or `src/lib/*/actions.ts`.
- **Returns:** Serializable data or `redirect()`. Revalidate via `revalidatePath()`/`revalidateTag()`.
- **Integration:** `useActionState` for progressive enhancement; `form.handleSubmitSafe()` with telemetry (see 4.1).
- **Details:** See `docs/development/forms.md` and `docs/development/server-actions.md`.

---

## 6. Testing and Quality Gates

### 6.1 Frontend testing

- **Principle:** Test behavior, not implementation. Lightest test that proves behavior: unit → component → API → integration → E2E.
- **Framework:** Vitest + jsdom, Playwright (e2e). Tests: `frontend/src/**/__tests__`; mocks: `frontend/src/test`; factories: `@/test/factories`.
- **Environment (MANDATORY):** `/** @vitest-environment jsdom */` first line for DOM/React; `node` for routes/actions.
- **MSW-first:** Network mocking via MSW only; never `vi.mock("fetch")`. Handlers in `frontend/src/test/msw/handlers/*`.
- **Mock order:** Mock `next/headers` BEFORE importing modules that read cookies. Use `vi.hoisted()` for spies.
- **Timers:** No global `vi.useFakeTimers()`; use `withFakeTimers` wrapper from `@/test/utils/with-fake-timers`.
- **AI SDK tests:** Use `MockLanguageModelV3`, `createMockModelWithTracking` from `@/test/ai-sdk/*`.
- **Coverage:** ≥85% overall; meet `frontend/vitest.config.ts` thresholds.
- **Details:** See `docs/development/testing.md`.

### 6.2 Quality gates (mandatory)

After any code change (`.ts`, `.tsx`, schema, config affecting builds), run in `frontend/`:

1. `pnpm biome:fix` — fix all issues; resolve any remaining errors manually.
2. `pnpm type-check` — must pass with zero errors.
3. `pnpm test:affected` — runs changed test files + tests related to changed source files; all must pass.

**Skip for:** doc-only (`.md`), comments, non-code config, questions, or analysis.

Do not return final response until all gates pass for code changes.

### Upstash testing

- **Mocking:** `setupUpstashMocks()` with `__reset()` in `beforeEach`. No ad-hoc mocks; use MSW handlers.
- **Commands:** `pnpm -C frontend test:upstash:{unit,int,smoke}`. See `frontend/src/test/upstash/` for emulator setup.

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
