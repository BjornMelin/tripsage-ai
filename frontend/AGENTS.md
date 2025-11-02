---
title: Frontend Agent Guidelines
---

## TypeScript Style, Biome, and Testing

- Follow Google’s TypeScript Style Guide. Enforce with `gts` or ESLint (`eslint-config-google` + `@typescript-eslint`). Keep imports, naming, and module structure per the guide.
- Document every exported file/symbol with JSDoc: top `@fileoverview`; `/** ... */` with accurate `@param`, `@returns`, `@throws`; use Markdown lists; match guide formatting and spacing.
- Use Biome as the single gate. Code must pass `biome check --write` with zero diagnostics; fail on warnings with `--error-on-warnings`. Keep a root `biome.json/jsonc`. Let Biome format, lint, and organize imports.
- Type-check clean on first pass: assume `strict: true` and `noEmit`; avoid `any`, handle null/undefined, enable `noUnusedLocals` and `noFallthroughCasesInSwitch`. Validate with `tsc --noEmit`.
- Tests: Vitest for unit/integration, Playwright for e2e. Use `**/*.{test,spec}.ts?(x)` globs. Separate with Vitest “projects” and set per-project environments (`node`, `jsdom`/`happy-dom`).
- CI runs: `vitest run` with coverage. Prefer `pool: 'threads'` for big suites; tune workers; keep per-file isolation by default and only disable (`--no-isolate`) when tests fully reset state.
- Coverage and reporting: provider `v8` by default; configure `coverage.include` and thresholds; emit `text`, `html`, `json` coverage; write machine-readable test results via `--reporter=junit` and `--outputFile`.
- Mocks and timers: use `vi.mock`, `vi.fn`, `vi.spyOn`; clear/restore in `afterEach`; control time with `vi.useFakeTimers()` and `vi.setSystemTime()`.

## Next.js 16, Supabase, shadcn/ui, Tailwind v4, and Upstash Redis

- Next.js 16 rendering: Use App Router and Route Handlers. Enable `cacheComponents` in `next.config`. Use `"use cache"` to cache stable data and components. Use tags for invalidation; call `revalidateTag` after writes in Server Actions or Route Handlers.
- Personalized data: For user-specific content, use `"use cache: private"` with `cacheLife` stale ≥30s and export `unstable_prefetch` for runtime prefetching. Never nest private caches inside public caches. If in doubt, treat as dynamic.
- Auth + SSR (Supabase): Use `@supabase/ssr`. Create two clients (`createServerClient` for Server Components/Actions/Route Handlers, `createBrowserClient` for Client Components). Call `cookies()` before any Supabase call to opt out of caching for auth flows. Use middleware to refresh tokens. Protect server pages with `supabase.auth.getUser()` (not `getSession()`).
- Auth confirmation: Add `app/auth/confirm/route.ts` to exchange `token_hash` for a session and redirect. Update email templates to point to `/auth/confirm`.
- Supabase UI: Prefer the official Supabase UI Library blocks (built on shadcn/ui) for auth, avatars, uploads, realtime, and list/query patterns. Use them as drop-in building blocks over hand-rolled forms.
- shadcn/ui setup: Initialize with the CLI, then add components. Keep `components.json` as the single source for theming options. Use `tailwind.cssVariables: true` to share CSS variables across app code and third-party blocks; set `rsc: true` for Server-Component-friendly variants when offered.
- Tailwind CSS v4: Install `tailwindcss` and `@tailwindcss/postcss`, import `@import "tailwindcss";` in global CSS, and define tokens with `@theme` (colors, radii, spacing, fonts). Prefer CSS-first configuration over legacy config files. Keep tokens minimal and semantic.
- Theming unification: Define design tokens once with Tailwind `@theme`. Consume via utilities and CSS variables. Align shadcn/ui and Supabase UI on the same token names to avoid per-component overrides.
- Upstash Redis: Use the Vercel integration to inject env vars, then connect with `Redis.fromEnv()` in Route Handlers/Server Components. Prefer the HTTP/REST client for Edge runtimes. Keep credentials server-only.
- Upstash usage: Use Redis for rate limits, counters, transient state, and small personalized caches. Do not use it as the Next.js server cache handler. After writes, tag domain data and trigger `revalidateTag` to refresh views.
- Caching rules with auth: Never wrap Supabase calls that read/set cookies in public caches. For user-specific prefetch, use `"use cache: private"` with required stale times; otherwise mark sections dynamic. Revalidate on mutation.
- CI defaults: Fail builds if any route uses private data without correct cache directives or if Supabase pages lack middleware/token refresh. Enforce coverage on auth flows, confirm routes, and cache-tagged mutations.

## Route Handlers, DI, and Testing

This repository standardizes Next.js App Router API code around thin adapters and dependency-injected handlers with deterministic Vitest tests.

### Guidelines (always apply)

- Thin Adapters: Keep files under `app/api/**/route.ts` minimal. They:
  - Parse `NextRequest` (headers/body)
  - Construct SSR-only clients (e.g., `createServerSupabase()`)
  - Lazily build rate limiters inside the handler (never at module scope)
  - Call a DI handler (`_handler.ts` or `_handlers.ts`) and return the result

- DI Handlers: Put business logic in `app/api/**/_handler.ts` or `_handlers.ts`:
  - Accept collaborators: `supabase`, `resolveProvider`, optional `limit` function, `logger`, `clock`, `config`
  - For AI streaming, accept `stream?: typeof streamText` so tests can inject a finite stub
  - Do not read `process.env` in handlers

- Rate Limiting:
  - Build Upstash `Ratelimit` inside the route, after env stubs/mocks are applied
  - Optionally cache lazily to avoid per-request construction

- AI SDK v6 Streaming:
  - Use `toUIMessageStreamResponse` in adapters/handlers
  - In tests, inject a stream stub or use `simulateReadableStream`; ensure streams close during tests

- Attachments:
  - Map UI file parts → model image parts with `convertToModelMessages` + `convertDataPart`
  - Validate media types (allow `image/*` only) in server routes

### Testing Rules

- Prefer handler unit tests with injected fakes:
  - `@vitest-environment node` for API tests
  - Inject stream stub for AI SDK tests to avoid open handles
  - Use shared fakes for Supabase/ratelimit/provider resolvers

- Adapter smoke tests:
  - Always `vi.resetModules()` and `vi.stubEnv()` BEFORE importing the route module
  - Mock `@upstash/ratelimit`, `@upstash/redis`, and SSR clients as needed
  - Keep to a minimum (401, 429 checks). Avoid hitting real streaming path

- Env Hygiene:
  - Use `vi.stubEnv` and `unstubAllEnvs()` helpers to avoid env leaks
  - Do not create Upstash clients at module scope

### File Structure Patterns

- `app/api/feature/route.ts` — thin adapter
- `app/api/feature/_handler.ts` or `_handlers.ts` — pure DI logic
- `app/api/_helpers/*.ts` — shared mapping/validation helpers
- Tests live under `__tests__` mirroring handler/adapter structure

### Rationale

- Aligns with Clean Architecture: “thin adapters, fat services”
- Stabilizes tests by eliminating module-scope side effects and open streams
- Keeps SSR-only concerns in adapters; handlers remain pure and portable
