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

### UI/Store Testing Conventions

- Deterministic inputs: provide stable timestamps and seeded data in UI tests. Use `vi.useFakeTimers()` + `vi.setSystemTime()` for date-dependent logic.
- Visible output assertions: prefer roles, text, and aria attributes. When components don’t expose roles for loaders, assert minimal stable selectors (e.g., `.animate-spin`) rather than brittle trees.
- No network: stub all fetch/external hooks; UI/store suites must not perform real network I/O.
- Store isolation: reset the Zustand store between tests using the store’s `reset()` action. Avoid asserting internal shapes; prefer public getters/actions. Where computed getters can be stale in hook snapshots, read via `useUIStore.getState()` or derive from the underlying state (e.g., `Object.values(loadingStates)` or `notifications.filter(n => !n.isRead)`).
- JSDOM vs Node: UI component tests run in JSDOM (default). Store-only tests can stay in JSDOM but must not depend on DOM APIs. Add `@vitest-environment` overrides only when necessary.
- Timers in stores: for auto-dismiss notifications, use fake timers and advance until removal to avoid real-time delays.
- Short runs: keep per-test timeouts short and eager; no unconsumed streams or pending async work.

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

Standardize API code around thin Next.js route adapters that delegate to pure, dependency-injected handlers. Keep effects in adapters; keep business logic in testable functions.

### Adapters

- Files: `app/api/**/route.ts`
- Parse `NextRequest` (headers/body) and construct SSR-only clients (e.g., `createServerSupabase()`).
- Build rate limiters lazily inside the request; never at module scope.
- Delegate to a DI handler (`_handler.ts` or `_handlers.ts`) and return `NextResponse`.

### DI Handlers

- Files: `app/api/**/_handler.ts` or `_handlers.ts`
- Pure functions that accept collaborators: `supabase`, `resolveProvider`, optional `limit`, `logger`, `clock`, `config`.
- No `process.env` reads, no module-scope state. For streaming, accept `stream?: typeof streamText` and return the injected result.

### Rate Limiting

- Construct Upstash `Ratelimit` inside the adapter using `Redis.fromEnv()`; optionally memoize per-request.
- Keep env/credential handling at the adapter boundary; pass `limit()` into the handler.

### Attachments and Model Messages

- Convert UI file parts to model parts (`convertToModelMessages` + `convertDataPart`).
- Validate media types (allow `image/*` only).

### Testing

- Handlers (unit): `@vitest-environment node`; inject fakes for Supabase/ratelimit/provider; ensure streams close; no network.
- Adapters (smoke): `vi.stubEnv` + `vi.resetModules` before import; mock `@upstash/ratelimit`, `@upstash/redis`, and SSR clients; validate 401/429 and happy-path wiring.
- Env hygiene: use helpers like `unstubAllEnvs()`; avoid module-scope clients.

### Structure

- `app/api/feature/route.ts` — thin adapter
- `app/api/feature/_handler.ts` or `_handlers.ts` — DI logic
- `app/api/_helpers/*.ts` — shared mappers/validators
- `__tests__/` — mirrors handlers/adapters

### Rationale

- Clean boundaries (“thin adapters, fat services”), deterministic tests (no module-scope effects), and portable handler logic.
