# AGENTS.md – TripSage AI Contract

This file defines required rules for all AI coding agents in this repo. If anything conflicts, **AGENTS.md wins**.

---

## 0. Architecture and Stack

- **Frontend-first:** All features at repository root. Next.js 16, React 19, TypeScript 5.9.
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

- **Primary app (root):** Next.js 16 workspace at repo root. Core AI in `src/app/api/**` route handlers. Shared schemas/types in `src/domain/schemas` (reuse server/client). Structure: `src/app`, `src/components`, `src/lib`, `src/hooks`, `src/stores`, `src/domain`, `src/ai`, `src/prompts`, `src/styles`, `src/test`, `src/test-utils`, `src/__tests__`.
- **Infrastructure:** Scripts in `scripts/`; containers in `docker/`; tests in `src/**/__tests__`; docs in `docs/`; e2e tests in `e2e/`.

---

## 4. Library-First Principles and Coding Style

### 4.1 Global engineering principles

- **Library-first:** Prefer maintained libraries covering ≥80 % of needs with ≤30 % custom code.
- **KISS / DRY / YAGNI:** Keep solutions straightforward; remove duplication via small focused helpers; implement only what's needed now—no speculative APIs or feature flags (unless requested).
- **Final-only:** Remove superseded code/tests immediately after new behavior lands; no partial migrations.
- **Telemetry/logging:** Use `@/lib/telemetry/{span,logger}` helpers: `withTelemetrySpan()`, `withTelemetrySpanSync()`, `recordTelemetryEvent()`, `createServerLogger()`, `emitOperationalAlert()`. Direct `@opentelemetry/api` only in `lib/telemetry/*` and `lib/supabase/factory.ts`. Client: `@/lib/telemetry/client`. See `docs/development/backend/observability.md`.
  - **Server code:** No `console.*` except test files and telemetry infra.
  - **Client-only UI (`"use client"` modules):** Dev-only `console.*` is allowed when guarded by `process.env.NODE_ENV === 'development'`. Bundlers eliminate these calls in prod builds.
  - **Zustand stores:** Use `createStoreLogger` from `@/lib/telemetry/store-logger` for error tracking via OTEL spans.

### 4.2 TypeScript and frontend style

- **TypeScript:** `strict: true`, `noUnusedLocals`, `noFallthroughCasesInSwitch`. Avoid `any`; use precise unions/generics. Handle `null`/`undefined` explicitly.
- **Unsafe casts:** `as unknown as T` casts are forbidden in production code (`src/**` excluding tests). CI runs `pnpm check:no-new-unknown-casts` to reject violations. Use type guards, schema validation, or `satisfies` instead. For test mocks requiring unsafe casts, use `unsafeCast<T>()` from `@/test/helpers/unsafe-cast`.
- **Secret scanning:** CI runs `pnpm check:no-secrets` on PR diffs and `pnpm check:no-secrets:full` on pushes (see `.github/workflows/ci.yml`). The script `check:no-secrets:staged` exists but is not used in workflows.
- **Biome:** `pnpm biome:fix`. Do **not** edit `biome.json`; fix code instead.
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
- **Details:** See `docs/development/standards/standards.md#zustand-stores` and `docs/development/frontend/zustand-computed-middleware.md`.

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
- **Details:** See `docs/development/standards/zod-schema-guide.md`.

---

## 5. Frontend Architecture and Patterns

### 5.1 Next.js route handlers and adapters

- Route Handlers: `src/app/api/**/route.ts` for all server‑side HTTP entrypoints.
- Adapters: parse `NextRequest`, construct SSR clients/ratelimiters/config **inside** handler (no module‑scope), delegate to DI handlers (`_handler.ts`).
- DI handlers: pure functions; accept `supabase`, `resolveProvider`, `limit`, `stream`, `clock`, `logger`, `config`. No `process.env` or global state.

**Import restrictions (scope: `src/app/api/**`):**

| Rule | Required | Exceptions |
|------|----------|------------|
| No direct `createClient` from `@supabase/supabase-js` | `createServerSupabase()` from `@/lib/supabase/server` | Tests, QStash handlers, scripts — use shared helper or add comment |
| No inline `NextResponse.json({ error })` | `errorResponse()` from `@/lib/next/route-helpers` | CLI tools, background handlers (non-route code) |

PR reviewers: enforce in `src/app/api/**`; approve exceptions with justification.

#### 5.1.1 Error response helpers

Use standardized helpers from `@/lib/api/route-helpers` for all error responses:

| Status | Helper | Use Case |
|--------|--------|----------|
| 401 | `unauthorizedResponse()` | Missing or invalid auth |
| 403 | `forbiddenResponse()` | Valid auth, insufficient permissions |
| 404 | `notFoundResponse()` | Resource doesn't exist |
| 4xx/5xx | `errorResponse({ error, reason, status })` | Validation, rate limits, server errors |

**Anti-patterns (avoid):**

- `NextResponse.json({ error: "..." }, { status: 4xx })` → use `errorResponse()`
- `new Response(JSON.stringify({ error }), ...)` → use `errorResponse()`

#### 5.1.2 Domain error classes

Prefer domain-specific error classes over string matching:

| Domain | Error Class | Location |
|--------|-------------|----------|
| Google Calendar | `GoogleCalendarApiError` | `@/lib/calendar/google` |
| Webhooks | `WebhookError` (+ subclasses) | `@/lib/webhooks/errors` |
| AI Tools | `ToolError` | `@ai/tools/server/errors` |
| API Responses | `ApiError` | `@/lib/api/error-types` |
| Accommodations | `ProviderError` | `@domain/accommodations/errors` |
| Activities | `NotFoundError` | `@domain/activities/errors` |

**Pattern:** Check domain error first, then generic:

```typescript
if (error instanceof GoogleCalendarApiError) {
  if (error.statusCode === 401) return handleTokenExpired();
  return errorResponse({ error: "calendar_error", reason: error.message, status: 400 });
}
throw error; // Let withApiGuards handle unknown errors
```

### 5.2 AI SDK v6 usage

- Use AI SDK v6 primitives only; no custom streaming/tool-calling.
- Chat/streaming: `convertToModelMessages()` → `streamText(tools, outputs)` → `result.toUIMessageStreamResponse()`.
- Structured JSON: use `generateObject` or `streamObject` with Zod schemas from `@schemas/*`.

### 5.3 Models and providers

- **Vercel AI Gateway (primary):** `createGateway()` with `AI_GATEWAY_API_KEY`.
- **BYOK registry (alternative):** `src/ai/models/registry.ts`; supports `openai`, `openrouter`, `anthropic`, `xai`.
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

- **Routes (SPEC-0029/ADR-0052):** `/api/config/agents/:agentType` (GET/PUT), versions, rollback. Source: `src/lib/agents/config-resolver.ts`.

### 5.7 Forms and Server Actions

- **Client forms:** `useZodForm` (`@/hooks/use-zod-form`), `useSearchForm`. Components: `Form`, `FormField`, `FormControl`, `FormMessage` from `@/components/ui/form`. Mode: `onChange`; use `form.trigger()` for programmatic validation/step gating; `AbortController` for async cleanup.
- **Server actions:** `"use server"` + `"server-only"` import; Zod validation; `createServerSupabase()`. Location: `src/app/(route)/actions.ts` or `src/lib/*/actions.ts`.
- **Returns:** Serializable data or `redirect()`. Revalidate via `revalidatePath()`/`revalidateTag()`.
- **Integration:** `useActionState` for progressive enhancement; `form.handleSubmitSafe()` with telemetry (see 4.1).
- **Details:** See `docs/development/frontend/forms.md` and `docs/development/backend/server-actions.md`.

---

## 6. Testing and Quality Gates

### 6.1 Frontend testing

- **Principle:** Test behavior, not implementation. Lightest test that proves behavior: unit → component → API → integration → E2E.
- **Framework:** Vitest + jsdom, Playwright (e2e). Tests: `src/**/__tests__`; mocks: `src/test`; factories: `@/test/factories`.
- **Playwright E2E:** Prefer `pnpm test:e2e:chromium` (Chromium-only). Use `pnpm test:e2e` for the full browser matrix. For Playwright CLI flags (headed/ui/grep), prefer `pnpm exec playwright ...` (pnpm script arg forwarding inserts `--`).
- **Environment (MANDATORY):** `/** @vitest-environment jsdom */` first line for DOM/React; `node` for routes/actions.
- **MSW-first:** Network mocking via MSW only; never `vi.mock("fetch")`. Handlers in `src/test/msw/handlers/*`.
- **Mock order:** Mock `next/headers` BEFORE importing modules that read cookies. Use `vi.hoisted()` for spies.
- **Timers:** No global `vi.useFakeTimers()`; use `withFakeTimers` wrapper from `@/test/utils/with-fake-timers`.
- **AI SDK tests:** Use `MockLanguageModelV3`, `createMockModelWithTracking` from `@/test/ai-sdk/*`.
- **Coverage:** ≥85% overall; meet `vitest.config.ts` thresholds.
- **Details:** See `docs/development/testing/testing.md`.

### 6.2 Quality gates (mandatory)

Before finalizing any work that includes code changes (`.ts`, `.tsx`, schemas, or config affecting builds), run at repository root:

1. `pnpm biome:fix` — fix all issues; resolve any remaining errors manually.
2. `pnpm type-check` — must pass with zero errors.
3. `pnpm test:affected` — runs changed test files + tests related to changed source files; all must pass.

**Skip for:** doc-only (`.md`), comments, non-code config, questions, or analysis.

Do not return final response until all gates pass for code changes.

**During iteration:** Prefer the smallest relevant shard (`pnpm test:unit`, `pnpm test:api`, `pnpm test:components`, `pnpm test:schemas`, `pnpm test:integration`). Run `pnpm test` only when changing test harness/config (e.g. `vitest.config.ts`, `src/test/**`) or before merging.

**Note:** `pnpm test` runs once (script: `vitest run`). For watch mode locally, use `pnpm exec vitest`.

**If Vitest hangs after finishing:** run `VITEST_DEBUG_OPEN_HANDLES=1 pnpm test` and ensure MSW is not bypassing unhandled requests (`MSW_ON_UNHANDLED_REQUEST=error`).

### 6.3 Dependency and bundle hygiene (recommended)

- **Unused deps (Knip):** `pnpm deps:report` (non-failing), `pnpm deps:audit` (failing), `pnpm deps:fix` (auto-removes unused deps from `package.json`).
- **Unused files (Knip):** `pnpm exec knip --files --no-exit-code` (review before deleting; if you automate deletion, require explicit opt-in via `--allow-remove-files`).
- **Bundle analysis (Next 16):** `pnpm build:analyze` (writes to `.next/diagnostics/analyze`).

### Upstash testing

- **Mocking:** `setupUpstashMocks()` with `__reset()` in `beforeEach`. No ad-hoc mocks; use MSW handlers.
- **Commands:** `pnpm test:upstash:{unit,int,smoke}`. See `src/test/upstash/` for emulator setup.

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

<!-- opensrc:start -->

## Source Code Reference

Source code for dependencies is available in `opensrc/` for deeper understanding of implementation details.

See `opensrc/sources.json` for the list of available packages and their versions.

Use this source code when you need to understand how a package works internally, not just its types/interface.

### Fetching Additional Source Code

To fetch source code for a package or repository you need to understand, run:

```bash
npx opensrc <package>           # npm package (e.g., npx opensrc zod)
npx opensrc pypi:<package>      # Python package (e.g., npx opensrc pypi:requests)
npx opensrc crates:<package>    # Rust crate (e.g., npx opensrc crates:serde)
npx opensrc <owner>/<repo>      # GitHub repo (e.g., npx opensrc vercel/ai)
```

<!-- opensrc:end -->
