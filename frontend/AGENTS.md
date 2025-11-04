# AGENTS.md — TripSage Frontend Agents Guide

Audience: engineers and AI agents working in this repository.

Scope: how to build, run, and test AI features with AI SDK v6, BYOK multi‑provider routing, Supabase SSR, Upstash Redis/Ratelimit, Tailwind v4, shadcn, Zod, Biome, and Vitest. This guide is authoritative for the `frontend/` workspace and supersedes earlier guidance.

---

## 0. Ground Rules

- Library‑first: prefer maintained libs that cover ≥80% needs with ≤30% custom code. Use AI SDK v6 primitives (streaming, tools, structured outputs) instead of bespoke orchestrators.
- KISS/DRY/YAGNI: keep adapters thin, handlers/services cohesive; avoid wrapping AI SDK streaming; don’t duplicate schema types between client/server—share Zod schemas.
- Repo gates: Biome formatting+linting, `tsc --noEmit`, and targeted Vitest. Treat warnings as failures; fix code rather than relaxing rules.
- Auth & caching: Next 16 `cacheComponents: true` is enabled; do not publicly cache auth‑dependent responses. Keep Supabase cookie reads in server contexts only.
- Evidence & safety: follow primary docs; don’t echo secrets; no client‑side env usage for server keys.

---

## Code Style and Quality

### TypeScript Style Guide (Google)

- Follow Google’s TypeScript Style Guide for imports, naming, module structure, comments, and docs. Enforce with Biome.
- File headers
  - Source files (`.ts`, `.tsx`): add `@fileoverview` only when it adds value (what/why, not code comments). Keep concise; do not indent wrapped lines.
  - Order: `@fileoverview` → blank line → `"use client"` (if present) → blank line → imports → implementation. Comments may appear above `"use client"`, but no code; keep exactly one blank line between sections.
  - Test files (`*.test.ts[x]`, `*.spec.ts[x]`): no `@fileoverview`. Use `/** @vitest-environment node */` only to override the default `jsdom` env.
- JSDoc/TSDoc
  - Use `/** ... */` for user‑facing docs; `//` for implementation notes.
  - Avoid `/* ... */` non‑JSDoc blocks; prefer multiple `//` lines instead.
  - JSDoc is Markdown. Use real lists; avoid pseudo‑indentation.
  - Put tags on their own lines; don’t combine multiple `@param` tags on one line.
  - When wrapping `@param`/`@return` text, indent wrapped lines by four spaces. Do not indent wrapped `@fileoverview` text.
  - Place JSDoc before decorators; never between a decorator and its target.
- What to document
  - All top‑level exports intended for consumption (APIs).
  - Functions/members where purpose is not obvious from names and types.
  - Do not duplicate TS types in JSDoc; avoid `@implements`, `@enum`, `@private`, `@override` in TS sources unless essential.
  - Document ctor parameter properties with `@param` so editors surface text at call sites.
- Call‑site comments: use `/* name= */` before values if needed; refactor to objects only when trivial and behavior‑preserving.

### Biome Configuration

- Single gate for formatting/lint/imports: `pnpm biome:check` (fail on warnings), `pnpm biome:fix`, `pnpm format:biome`.
- Do not change `biome.json` unless explicitly requested. Fix code, don’t relax rules.
- Key settings (see `frontend/biome.json:1`): lineWidth 88; 2‑space indent; LF; double quotes; ES5 trailing commas; strict naming; `noExplicitAny`; unused variables/imports forbidden; React hook/exhaustive‑deps enabled.

### Type Checking

- Strict TS (`pnpm type-check` → `tsc --noEmit`). Avoid `any`; handle null/undefined; `noUnusedLocals`, `noFallthroughCasesInSwitch` apply.

---

## 1. Stack and Versions (source of truth: package.json)

- Next.js `16.0.1`; React `19.2.0`.
- AI SDK core `ai@6.0.0-beta.92`; UI hooks `@ai-sdk/react@3.0.0-beta.92`.
- Providers: `@ai-sdk/openai@3.0.0-beta.47`, `@ai-sdk/anthropic@3.0.0-beta.47`.
- Styling: Tailwind CSS `4.1.15` with `@tailwindcss/postcss` and CSS‑first imports.
- Data/Auth: `@supabase/ssr@0.7.0` and `@supabase/supabase-js@2.76.x`.
- Ratelimit & cache: `@upstash/ratelimit@2.0.6`, `@upstash/redis@1.35.x`.
- Types & schemas: TypeScript `5.9.x`, Zod `4.1.12`.
- Quality & tests: Biome `2.3.2`, Vitest `4.0.1` (+ Playwright for e2e).

---

## 2. Models and Providers

### 2.1. BYOK provider registry (primary)

- Source: `frontend/src/lib/providers/registry.ts:1`.
- Resolves user‑specific keys server‑side and returns a ready `LanguageModel` for AI SDK v6.
- Supported providers: `openai`, `openrouter`, `anthropic`, `xai` (OpenAI‑compatible for xAI).
- Defaults (subject to change): `openai → gpt-4o-mini`, `anthropic → claude-3-5-sonnet-20241022`, `openrouter → openai/gpt-4o-mini`.
- Usage pattern (Route Handler):

```ts
import type { NextRequest } from "next/server";
import { resolveProvider } from "@/lib/providers/registry";
import { convertToModelMessages, streamText } from "ai";

export async function POST(req: NextRequest) {
  const { userId, messages, model } = await req.json();
  const { model: llm } = await resolveProvider(userId, model);
  const result = await streamText({
    model: llm,
    messages: convertToModelMessages(messages),
  });
  return result.toUIMessageStreamResponse();
}
```

### 2.2. Optional: Vercel AI Gateway

- Benefits: OpenAI‑compatible endpoints, multi‑provider routing, retries, budgets, observability.
- Configure via `createOpenAI({ baseURL: "https://ai-gateway.vercel.sh/v1", apiKey: process.env.AI_GATEWAY_API_KEY })`. Primary docs: vercel.com/docs/ai-gateway (OpenAI‑compatible API).
- When adopting Gateway, keep a single routing path (either BYOK or Gateway) for simplicity; don’t mix per‑route.

---

## 3. AI SDK v6 Patterns

### 3.1 Streaming route with tools

- Use Next.js Route Handlers; keep side‑effects in the adapter; define tools with Zod; stream tokens.
- Return `result.toUIMessageStreamResponse()` for compatibility with `@ai-sdk/react` UI.

```ts
import { z } from "zod";
import { tool, streamText, Output, convertToModelMessages } from "ai";
import { openai } from "@ai-sdk/openai"; // or a model from resolveProvider

export async function POST(req: Request) {
  const { messages } = (await req.json()) as { messages: unknown };
  const weather = tool({
    description: "Get weather in a city",
    parameters: z.object({ city: z.string().min(1) }),
    execute: async ({ city }) => ({ city, tempC: 22 }),
  });
  const result = await streamText({
    model: openai("gpt-4o"),
    messages: convertToModelMessages(messages),
    tools: { weather },
    output: Output.object({ schema: z.object({ summary: z.string() }) }),
  });
  return result.toUIMessageStreamResponse();
}
```

### 3.2 Structured JSON without tools

- Use `generateObject`/`streamObject` with Zod when a typed object is the final output.

```ts
import { z } from "zod";
import { generateObject } from "ai";
import { openai } from "@ai-sdk/openai";

const TripPlan = z.object({ title: z.string(), days: z.array(z.object({ date: z.string(), items: z.array(z.string()) })) });

export async function planTrip(userText: string) {
  const { object } = await generateObject({ model: openai("gpt-4o"), schema: TripPlan, prompt: `Extract a minimal trip plan from:\n${userText}` });
  return object;
}
```

Notes: `streamText`, tools, `Output.object`, `generateObject`, and `toUIMessageStreamResponse()` are documented in AI SDK v6 (ai-sdk.dev).

### 3.3 Library specifics and migration notes

- Messages: always convert UI messages server‑side with `convertToModelMessages(messages)`.
- Attachments: map UI file parts to model data with `convertDataPart` (when sending binary) or pass URLs; validate media types on the server (accept `image/*` only).
- Streaming
  - v6 streams by default; the old `toolCallStreaming` flag is removed.
  - Return `result.toUIMessageStreamResponse()` for `@ai-sdk/react` compatibility. For custom merging (adding data annotations, sources), use `createUIMessageStreamResponse` and merge `result.toUIMessageStream()` into a writer.
- Structured outputs
  - With tools: `output: Output.object({ schema })` validates the final object after the run.
  - Without tools: prefer `generateObject`/`streamObject`. `streamObject` exposes `partialObjectStream` for progressive UI.
- Token budgeting: clamp output tokens using local helpers where applicable; see `frontend/src/app/api/chat/_handler.ts:1` and `frontend/src/app/api/ai/stream/route.ts:1` for `clampMaxTokens`, `countTokens`, `countPromptTokens`, and `getModelContextLimit` usage.

---

## 4. Client UI

- Hooks: `useChat` from `@ai-sdk/react` manages chat state and streaming.
- Transport: prefer `DefaultChatTransport` with `api: "/api/chat/stream"` for resumable streams.
- UI primitives live under `src/components/ai-elements/*` (Message, Response, PromptInput, Sources, etc.); use these instead of external AI Elements packages.
- Reference: `frontend/src/app/chat/page.tsx:1` shows end‑to‑end usage with resumable streams and attachments.

---

## 5. Next.js 16 Caching and Supabase SSR

### 5.1. Caching

- `cacheComponents: true` is enabled in `frontend/next.config.ts:1`. With Cache Components, data fetching in App Router is excluded from pre‑renders unless explicitly cached.
- Use `'use cache'` to cache at file/component/function level. For user‑specific data, prefer `'use cache: private'`.
- Use `cacheTag()` to tag cached results; call `revalidateTag(tag)` on writes to invalidate. Prefer tag invalidation over broad revalidation; use `revalidatePath` when invalidating whole routes.
- For dynamic results that must always be fresh, omit `'use cache'` and rely on runtime fetches. Be aware this can add latency vs. serving pre‑rendered content.
- Understand caches and lifetimes: Request Memoization (per request), Data Cache (persistent; revalidatable), Full Route Cache (HTML/RSC payload), Router Cache (client‑side). See Next.js Caching Guide for details.
- Avoid public caching for any route that reads or sets cookies/headers.

### 5.2. Prefetch and Router Cache

- Next automatically prefetches route assets for `next/link` in viewport. Keep links within the viewport minimal and meaningful.
- Consider hover‑triggered prefetch for menus and dense link lists; disable prefetch for very heavy routes.
- Rely on the Router Cache for fast client‑side transitions; do not manually bypass it unless debugging.

### 5.3. Supabase SSR auth

- Server client factory: `frontend/src/lib/supabase/server.ts:1` binds cookies for App Router.
- Middleware: `frontend/middleware.ts:1` refreshes the session and synchronizes cookies. Keep auth refresh centralized here to avoid race conditions.
- Never access Supabase cookies in client components.

Docs: supabase.com/docs (SSR client + Next.js middleware examples).

---

## 6. Next.js Performance Optimizations

- Fonts: use `next/font` to self‑host Google or local fonts; prefer variable fonts and minimal subsets in Root Layout. Reduces layout shift and removes external font requests.
- Images: use `next/image` with proper `sizes`, `priority` for LCP images, and `placeholder="blur"` for perceived performance. Declare `remotePatterns` where needed; avoid `dangerouslyAllowSVG` unless required.
- Code splitting: keep most components as Server Components by default; mark Client Components only where interaction is needed to reduce JS shipped to the browser.
- Dynamic import: use `next/dynamic` for heavy Client Components and non‑critical UI; consider `ssr: false` only for truly browser‑only dependencies.
- Imports: leverage `optimizePackageImports` (already enabled) to minimize bundle cost of large libraries.
- Scripts: use `next/script` with `afterInteractive`, `lazyOnload`, or `beforeInteractive` as appropriate for third‑party scripts.
- Compiler: `reactCompiler: true` is enabled. Keep components pure and prefer stable references (avoid mutating props/closures) to help the compiler.

Docs: Next.js cacheComponents, caching, prefetching, image and font optimization, Link component, React Compiler.

---

## 7. Rate Limiting and Ephemeral State

- Use `@upstash/ratelimit` + `@upstash/redis`. Initialize inside the request adapter (not module scope). Prefer `Redis.fromEnv()`.
- Example: see `frontend/src/app/api/chat/route.ts:1` and stream routes under `frontend/src/app/api/**/route.ts`.

Docs: Upstash ratelimit examples and templates.

---

## 8. Styling and UI System

- Tailwind v4 with `@tailwindcss/postcss`; import via `@import "tailwindcss";` (see `frontend/postcss.config.mjs:1` and `frontend/src/app/globals.css:1`).
- The project uses CSS custom properties (`@layer base`) for theming; continue to define tokens here. Tailwind v4 `@theme` tokens are optional for new work.
- shadcn is configured via `frontend/components.json:1` with `rsc: true` and `cssVariables: true`.

Docs: tailwindcss.com (Functions & directives; v4 blog), ui.shadcn.com.

---

## 9. Quality Gates and Commands

- Format/lint: `pnpm biome:check` (fail on warnings), `pnpm biome:fix`, `pnpm format:biome`.
- Types: `pnpm type-check` runs `tsc --noEmit`.
- Tests: run targeted suites only — `pnpm test:run` (or `pnpm test` during dev), `pnpm test:coverage` when requested, `pnpm test:e2e` for Playwright.
- Build/dev: `pnpm build`, `pnpm build:analyze`, `pnpm dev`, `pnpm start`.

Do not change Biome rules unless explicitly requested; fix code instead.

---

## 10. Testing Guidance

- Framework: Vitest with jsdom default, V8 coverage, strict timeouts. Config at `frontend/vitest.config.ts:1`.
- Vitest specifics: `isolate: true`, `bail: CI?5:0`, `pool: "threads"`, `maxWorkers: CI?2:1`, `testTimeout: 7500`, `hookTimeout: 12000`, coverage thresholds (global: lines 90, statements 90, functions 90, branches 85), reporters `text,json,html,lcov`. Include patterns `**/*.{test,spec}.ts?(x)` and exclude `**/e2e/**`.
- Aliases: `server-only` is shimmed in tests; use it to import server‑only modules safely.
- Global setup: `frontend/src/test-setup.ts:1` wires `@testing-library/jest-dom`, mocks Next navigation/router, Supabase browser client, toast hooks, storage, `matchMedia`, observers, and `console`; restores mocks after each test.
- No real network calls. Mock `streamText`, provider factories, Supabase, and Upstash at the adapter boundary. See tests under `frontend/src/app/api/**/__tests__` and `frontend/src/lib/**/__tests__`.
- Env hygiene: prefer `vi.stubEnv` and `vi.resetModules` before importing route adapters to exercise env‑dependent paths; clean up with provided helpers.

---

## 11. Security, Privacy, and PII

- Do not expose secrets in prompts, logs, or client code. Never echo `process.env` values.
- Keep provider keys server‑side (BYOK registry). When using Gateway, use the Gateway API key, not raw provider keys, on the server only.
- Do not public‑cache responses that read or set cookies.

---

## 12. KISS/DRY/YAGNI Pitfalls to Avoid

- Re‑implementing streaming, tool calling, or retries — use AI SDK v6.
- Duplicating Zod types across client/server — export schemas from `src/schemas`.
- Module‑scope clients or ratelimiters in Route Handlers — build inside the request.
- Mixing provider routing strategies — pick BYOK (primary) or Gateway per deployment.
- Public caching of auth‑dependent data.

---

## 13. Checklists

- Server routes:
  - Next Route Handler; DI resolver for model; `streamText`; Upstash limit inside request; `toUIMessageStreamResponse()`.
  - No module‑scope state; typed inputs; explicit 4xx on validation errors.
- Client:
  - `useChat` with `DefaultChatTransport` to `/api/chat/stream`; local `ai-elements/*` components for UI; no secrets.
- Schemas:
  - Share Zod via `src/schemas`; avoid duplication.
- Tests:
  - Targeted Vitest runs; no network; mock AI SDK/Upstash/Supabase as needed.
- Style:
  - Biome clean; TypeScript strict; minimal JSDoc (no duplicate types).

---

## 14. React 19 Guidance

- React Compiler
  - Enabled via `reactCompiler: true` in Next config. The compiler automatically optimizes re‑renders, reducing the need for `memo`/`useMemo`/`useCallback` in many cases.
  - Keep components pure; avoid mutating props/state; prefer stable object/array references or derive from props.
  - Avoid creating new inline closures that capture changing values when possible; the compiler handles many cases, but stable inputs improve results.
  - Optional: adopt the ESLint plugin for React Compiler to surface anti‑patterns early.
- Data fetching & Effects
  - Prefer Server Components (and Route Handlers/Server Actions) for data fetching. Avoid `useEffect` for server‑fetchable data and imperative DOM reads.
  - Use Suspense boundaries to stream slow UI; colocate Suspense near components that fetch.
  - Use transitions for non‑urgent updates to keep UI responsive.
- Actions and optimistic UX
  - Use `useActionState` for form actions that return state.
  - Use `useOptimistic` for immediate UI feedback while server actions complete.

Docs: react.dev — React Compiler introduction, `useActionState`, `useOptimistic`.

---

## 15. Decision Framework (weighted)

Weights: Solution Leverage 35%, Application Value 30%, Maint./Cognitive Load 25%, Adaptability 10%.

- A. BYOK multi‑provider (current): 8/10 leverage, 8/10 value, 8/10 load, 7/10 adaptability → Total ≈ 8.0.
- B. Vercel AI Gateway (optional): 9/10 leverage, 9/10 value, 7/10 load, 9/10 adaptability → Total ≈ 8.6 (recommended for centralized routing/observability).
- C. Single‑provider direct only: 7/10 leverage, 7/10 value, 8/10 load, 6/10 adaptability → Total ≈ 7.3.

Rationale: Gateway slightly leads for multi‑provider control and observability. We keep BYOK as primary to match current implementation; adopt Gateway when budgets/fallbacks/metrics are required.

---

## 16. Repo References

- Providers: `frontend/src/lib/providers/registry.ts:1`.
- Supabase SSR: `frontend/src/lib/supabase/server.ts:1`, `frontend/middleware.ts:1`.
- Streaming routes: `frontend/src/app/api/ai/stream/route.ts:1`, `frontend/src/app/api/chat/stream/route.ts:1`.
- Non‑stream route: `frontend/src/app/api/chat/route.ts:1`.
- Chat UI example: `frontend/src/app/chat/page.tsx:1`.
- Tailwind + global tokens: `frontend/postcss.config.mjs:1`, `frontend/src/app/globals.css:1`.
- Config: `frontend/next.config.ts:1`, `frontend/biome.json:1`, `frontend/vitest.config.ts:1`, `frontend/package.json:1`.

---

## 17. Useful Docs

- AI SDK v6 (core/tools/structured output/testing/UI): <https://ai-sdk.dev>
- Vercel AI Gateway (OpenAI‑compatible): <https://vercel.com/docs/ai-gateway/openai-compat>
- Supabase SSR + Next middleware: <https://supabase.com/docs/guides/auth/server-side/creating-a-client>
- Tailwind v4 functions & directives: <https://tailwindcss.com/docs/functions-and-directives>
- Upstash ratelimit examples: <https://vercel.com/templates/next.js/ratelimit-with-upstash-redis>
- Next.js Cache Components: <https://nextjs.org/docs/app/api-reference/config/next-config-js/cacheComponents>
- Next.js `use cache` directive: <https://nextjs.org/docs/app/api-reference/directives/use-cache>
- Next.js Caching Guide: <https://nextjs.org/docs/app/guides/caching>
- Next.js Prefetching Guide: <https://nextjs.org/docs/app/guides/prefetching>
- Next.js Image Optimization: <https://nextjs.org/docs/app/getting-started/images>
- Next.js Font Optimization: <https://nextjs.org/docs/app/getting-started/fonts>
- Next.js React Compiler config: <https://nextjs.org/docs/app/api-reference/config/next-config-js/reactCompiler>
- React Compiler intro: <https://react.dev/learn/react-compiler/introduction>
- React `useActionState`: <https://react.dev/reference/react/useActionState>
- React `useOptimistic`: <https://react.dev/reference/react/useOptimistic>
