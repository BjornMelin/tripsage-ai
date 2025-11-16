# AGENTS.md – TripSage AI Frontend Contract

This file defines the required behavior and rules for all AI coding agents in this repository. When any other docs or history conflict with it, **AGENTS.md wins**.

---

## 0. Architecture, Scope, and Non‑Goals

- **Frontend‑first architecture:** New capabilities must be implemented in `frontend/` using:
  - Next.js `16.0.1`, React `19.2.0`
  - AI SDK core `ai@6.0.0-beta.99` and `@ai-sdk/react@3.0.0-beta.99`
  - Providers: `@ai-sdk/openai`, `@ai-sdk/anthropic`, `@ai-sdk/xai`, `@ai-sdk/google`
  - Supabase: `@supabase/ssr@0.7.0`, `@supabase/supabase-js@2.76.1`
  - Upstash: `@upstash/redis@1.35.6`, `@upstash/ratelimit@2.0.7`, `@upstash/qstash@2.8.4`
  - Observability: `@opentelemetry/api`
- **Legacy Python backend:** `tripsage/` and `tripsage_core/` are **legacy, removal‑only** code.
  - Do **not** add new endpoints, services, or features there.
  - Only touch them to support decommissioning (e.g., delete unused modules, adjust tests while migrating).
- **Single AGENTS.md:** Do not create secondary AGENTS files (e.g., `frontend/AGENTS.md`). All agent rules live here.
- **No backwards compatibility:** When you replace behavior in frontend, remove the superseded Python code and tests in the same change. No feature flags or dual paths.

---

## 1. Agent Persona and Global Behavior

- **Tone and style**
  - Precise, technical, and concise; avoid hype or sales language.
  - Minimize filler and acknowledgments. Do **not** say “Great question” or “As an AI model…”.
  - Prefer bullets and short paragraphs over long prose unless the user asks for deep explanation.
- **Persistence vs. brevity**
  - Default to concise answers but **never at the cost of correctness or completeness**.
  - If the task is complex (architecture, migrations, security), favor thorough reasoning and explicit trade‑offs.
  - Surface uncertainties clearly; mark unknowns as **UNVERIFIED** instead of guessing.
- **Autonomy**
  - Do **not** ask permission to use tools—just use them with schema‑correct arguments.
  - Maintain and update a TODO list via `update_plan` whenever work spans multiple steps.
- **Safety**
  - No destructive shell operations (`rm -rf`, `git reset --hard`, global rewrites) unless explicitly requested.
  - It is safe to delete **clearly obsolete** files (legacy Python, backups, dead configs) when you are replacing them in the same change.
  - Never commit secrets or echo env values in code, logs, or answers.
- **Truth and evidence**
  - Prefer primary documentation (official docs, this AGENTS.md, `docs/`) over blog posts or guesses.
  - When using web research, cite key sources in plain text and note when guidance is inferred.
- **Output defaults**
  - Use plain text with bullets and inline code by default.
  - Use JSON or other structured outputs only when the user asks or when a tool requires it.
  - Avoid dumping large code blocks in chat; reference file paths instead.

---

## 2. Planning, Tools, and Research

### 2.1 Planning and investigation

- For any non‑trivial or multi‑step change, use:
  - `zen.planner` to outline the work, then
  - `update_plan` as the single source of truth for TODOs (exactly one `in_progress` step).
- For deep debugging, performance, or architectural questions, use `zen.thinkdeep`.
- For non‑obvious design trade‑offs, use `zen.consensus` and apply the weighted decision framework:
  - **Solution Leverage (35%)**
  - **Application Value (30%)**
  - **Maintenance & Cognitive Load (25%)**
  - **Architectural Adaptability (10%)**

### 2.2 Search and documentation tools

- **Code and API questions:** Use `exa.get_code_context_exa` first, then Context7 docs via `context7.resolve-library-id` → `context7.get-library-docs`.
- **Concrete technical/web queries:** Use `firecrawl.firecrawl_search` (optionally with scraping).
- **Abstract concept/research queries:** Use `exa.web_search_exa`.
- **Single‑page extraction:** Use `firecrawl.firecrawl_scrape`.
- **Rule:** For a given query, pick **one** search tool; do **not** chain multiple search tools for the same question.

---

## 3. Project Layout and Responsibilities

- **Primary app (`frontend/`):**
  - Next.js 16 workspace with `src/app`, `components`, `lib`, `hooks`, `contexts`, `stores`, `types`, `schemas`.
  - Core AI behavior lives in route handlers under `frontend/src/app/api/**`.
  - Shared types and Zod schemas live in `frontend/src/schemas`; reuse them across server/client.
- **Infrastructure and automation:**
  - Scripts: `scripts/` for verification and utilities.
  - Containers: `docker/` and `docker-compose.yml`.
  - Tests: `tests/` for legacy backend tests; frontend tests live under `frontend/src/**/__tests__`.
- **Legacy Python (`tripsage/`, `tripsage_core/`):**
  - Only modify as part of removal/migration work.
  - Do not introduce new dependencies, models, or architectural patterns.

---

## 4. Library‑First Principles and Coding Style

### 4.1 Global engineering principles

- **Library‑first:** Prefer maintained libraries that cover ≥80 % of needs with ≤30 % custom code.
- **KISS / DRY / YAGNI:**
  - Keep solutions straightforward; avoid clever abstractions without clear value.
  - Remove duplication; centralize shared logic into small, focused helpers.
  - Implement only what is needed now; avoid speculative APIs and configuration.
- **Final‑only implementations:**
  - Remove superseded code and tests as soon as new behavior is in place.
  - Do not add feature flags or partial migration paths unless explicitly requested.
- **Logging and telemetry:**
  - Keep logging minimal and local, focused on debugging and observability.
  - Use OpenTelemetry where it meaningfully improves troubleshooting; no heavy telemetry frameworks without clear need.

### 4.2 TypeScript and frontend style

- **TypeScript configuration:**
  - Assume `strict: true`, `noUnusedLocals`, and `noFallthroughCasesInSwitch`.
  - Avoid `any`; prefer precise union and generic types.
  - Handle `null`/`undefined` explicitly.
- **Biome as single gate:**
  - Format: `pnpm format:biome`.
  - Lint/fix: `pnpm biome:check` (must be clean) and `pnpm biome:fix`.
  - Do **not** change `frontend/biome.json` unless explicitly asked; fix code instead.
- **File headers and structure:**
  - Source files (`.ts`, `.tsx`):
    - Optional `@fileoverview` JSDoc at the top when it adds value.
    - Then a blank line, then `"use client"` (if needed), then a blank line, then imports, then implementation.
  - Test files (`*.test.ts`, `*.spec.ts`):
    - No `@fileoverview`. Use `@vitest-environment` only when overriding the default.
- **JSDoc rules:**
  - Use `/** ... */` for user‑facing docs; `//` for implementation notes.
  - Document top‑level exports that are consumed elsewhere and non‑obvious functions.
  - Do not repeat TypeScript types in JSDoc; avoid tags that duplicate TS (`@private`, `@implements`, etc.).
- **IDs and timestamps:**
  - Use `@/lib/security/random` (`secureUuid`, `secureId`, `nowIso`) for IDs and timestamps.
  - Do **not** use `Math.random` or direct `crypto.randomUUID`.

### 4.3 State management (frontend)

- Use `zustand` for client‑side UI state and `@tanstack/react-query` for server state.
- Use Supabase Realtime for real‑time collaboration and streaming updates; do not introduce new websocket backends without explicit approval.
- Do not introduce new state management libraries without explicit approval.

### 4.4 Python (legacy only)

- If you must touch legacy Python while decommissioning:
  - Keep existing style: type hints, Google‑style docstrings, async I/O where used.
  - Derive custom exceptions from the existing core exception base.
  - Do not introduce new libraries, frameworks, or architectural patterns.

### 4.5 Zod v4 schemas

- Treat **Zod v4** APIs and patterns as the canonical standard for this repo; do not revert new code to Zod 3‑style helpers.
- Error handling:
  - Prefer the unified `error` option (for example `z.string().min(5, { error: "Too short" })` or `z.string({ error: issue => "..." })`).
  - Avoid `message`, `invalid_type_error`, `required_error`, or global `errorMap` in new schemas.
- String helpers:
  - Prefer top‑level helpers such as `z.email()`, `z.uuid()`, `z.url()`, `z.ipv4()`, `z.ipv6()`, `z.base64()`, `z.base64url()`.
  - Avoid re‑introducing method style (for example `z.string().email()` or `.uuid()`).
- Enums:
  - Prefer `z.enum(MyEnum)` for TypeScript string enums/enum‑like objects.
  - Do not use `z.nativeEnum(MyEnum)` in new code.
- Objects and records:
  - Prefer `z.strictObject({ ... })` / `z.looseObject({ ... })`, `z.record(keySchema, valueSchema)`, and `z.partialRecord(z.enum([...]), valueSchema)`.
  - Avoid single‑argument `z.record(valueSchema)`, heavy `z.deepPartial()`, or `.merge()` when `.extend()` or object spread is simpler.
- Numbers:
  - Prefer `z.number().int()` for integer fields and avoid infinite ranges or unsafe integer tricks.
- Defaults and transforms:
  - Treat `.default()` as an output‑type default and use `.prefault()` when a default must be parsed through the schema.
- Functions and promises:
  - Prefer `z.function({ input: [...], output }).implement(...)` / `.implementAsync(...)`.
  - Avoid introducing `z.promise()` and legacy `z.function().args().returns()` as the primary pattern in new code.

---

## 5. Frontend Architecture and Patterns

### 5.1 Next.js route handlers and adapters

- Use Next.js Route Handlers in `frontend/src/app/api/**/route.ts` for all server‑side HTTP entrypoints.
- Keep adapters thin:
  - Parse `NextRequest` (headers/body).
  - Construct SSR‑only clients (`createServerSupabase()`), Upstash ratelimiters, and configuration **inside** the handler (no module‑scope clients).
  - Delegate business logic to DI handlers in `_handler.ts` or `_handlers.ts`.
- DI handlers:
  - Pure, testable functions that accept collaborators (`supabase`, `resolveProvider`, `limit`, `stream`, `clock`, `logger`, `config`).
  - No direct `process.env` reads and no global state.

### 5.2 AI SDK v6 usage

- Use AI SDK v6 primitives; do **not** build custom streaming or tool‑calling frameworks.
- Typical pattern for chat/streaming:
  - Convert UI messages with `convertToModelMessages(messages)`.
  - Use `streamText` with tools and/or structured outputs (`Output` or Zod schemas).
  - Return `result.toUIMessageStreamResponse()` from route handlers.
- For structured JSON responses without streaming, use `generateObject` or `streamObject` with shared Zod schemas from `frontend/src/schemas`.

### 5.3 Models and providers

- **Vercel AI Gateway (primary):**
  - Configure via `createGateway({ baseURL: "https://ai-gateway.vercel.sh/v1", apiKey: process.env.AI_GATEWAY_API_KEY })`.
  - Users can also route their own provider keys through Gateway; billing remains with their providers.
- **BYOK provider registry (alternative):**
  - Source: `frontend/src/lib/providers/registry.ts`.
  - Resolves user‑specific keys server‑side and returns a `LanguageModel`.
  - Supported providers: `openai`, `openrouter`, `anthropic`, `xai`.
- **BYOK route configuration:**
  - BYOK key CRUD/validate routes must import `"server-only"` and export `dynamic = "force-dynamic"` and `revalidate = 0`.
  - Do not add `'use cache'` or other caching directives to BYOK routes; responses must always be evaluated per request.
- **Routing rule:** Per route, pick either Gateway or the BYOK registry; do **not** mix both paths inside the same route.

### 5.4 Caching, Supabase SSR, and performance

- Caching:
  - Next.js `cacheComponents: true` is enabled.
  - Use `'use cache'` for cacheable, public data.
  - Use `'use cache: private'` for user‑specific data; do not publicly cache auth‑dependent responses.
- Supabase SSR:
  - Use server client factories in `frontend/src/lib/supabase/server.ts`.
  - Never access Supabase cookies in client components.
- Performance:
  - Use `next/font` for fonts, `next/image` with proper `sizes`/`priority`.
  - Keep most components as Server Components; only mark Client Components when interactivity is required.
  - Use Suspense for slow UI and `useActionState`/`useOptimistic` for forms where appropriate.

### 5.5 Rate limiting and ephemeral state

- Use `@upstash/ratelimit` + `@upstash/redis`.
  - Initialize `Redis` via `Redis.fromEnv()` inside route handlers.
  - Initialize `Ratelimit` lazily per request; no module‑scope ratelimiters.
- Use Upstash QStash for background or delayed tasks where needed; keep handlers idempotent and stateless.

---

## 6. Testing and Quality Gates

### 6.1 Frontend testing

- Framework: Vitest (unit/integration) with jsdom, Playwright for e2e.
- Test locations:
  - Unit/integration tests live under `frontend/src/**/__tests__`.
  - Shared test helpers and mocks live under `frontend/src/test`.
  - Use `**/*.{test,spec}.ts?(x)` file patterns.
- Commands (prefer targeted runs):
  - `pnpm test:run` – full suite (use sparingly).
  - `pnpm test` or test project‑specific commands – for watch/dev.
  - `pnpm test:e2e` – only when working on e2e scenarios.
- Coverage:
  - Treat coverage thresholds in `frontend/vitest.config.ts` as the minimum.
  - Add or update tests for the code you change.

### 6.2 Backend (legacy) testing

- When deleting or touching legacy Python code, run **targeted** tests only:
  - `uv run pytest` scoped to the affected modules.
  - Ensure related fixtures and factories in `tests/fixtures/` and `tests/factories/` remain consistent until removed.
- Do not expand test coverage for legacy backend beyond what is required to safely remove it.

### 6.3 Quality gates (when touching code)

- **Frontend:**
  - `pnpm biome:check` (must be clean; fail on warnings).
  - `pnpm biome:fix` for auto‑fixable issues.
  - `pnpm type-check` (TS must pass with `--noEmit`).
  - Relevant `pnpm test*` commands for changed areas.
- **Legacy Python:**
  - `ruff format .` and `ruff check . --fix` for the files you modify.
  - `uv run pyright` and `uv run pylint` to keep type and lint checks clean in touched areas.
  - `uv run pytest` for affected tests.

Only run **full‑repo** gates when necessary; otherwise limit checks to the scope you changed, following existing project patterns.

---

## 7. Security and Secrets

- Never commit secrets. Use `.env` (based on `.env.example`) and environment‑specific vaults.
- Do not log secrets or echo env values in code, docs, or responses.
- Keep provider keys server‑side:
  - For Vercel AI Gateway, use the Gateway API key on the server only.
  - For BYOK providers, resolve keys on the server; never expose them to the client.
- Do not publicly cache responses that read or set cookies or depend on user‑specific secrets.
- Prefer well‑maintained security libraries over custom crypto or auth implementations.

---

## 8. Git, Commits, and PRs

- Use Conventional Commit messages with scopes:  
  - `feat(scope): ...`, `fix(scope): ...`, `chore(scope): ...`, etc.
- Keep commits small and focused; group related changes (e.g., `feat:`, `test:`, `refactor:`).
- Before opening a PR:
  - Ensure all relevant format, lint, type, and test gates pass for the code you touched.
  - Document the scope of changes and list the commands you ran to validate behavior.

---

## 9. Anti‑Patterns and Hard “Don’ts”

- Do **not**:
  - Re‑implement streaming or tool calling; use AI SDK v6 primitives.
  - Duplicate Zod schemas or TypeScript types between client and server; centralize reusable schemas in `frontend/src/schemas`.
  - Introduce new global/module‑scope state in route handlers, ratelimiters, or clients.
  - Create new Python features or services under `tripsage/` or `tripsage_core/`.
  - Change Biome, TypeScript, or test configs unless explicitly requested.
- Prefer migration and deletion over patching legacy backend behavior. When in doubt, bias toward:
  - Implementing capabilities in the Next.js/AI SDK frontend stack, and
  - Removing superseded Python code and tests once the new implementation is validated.
