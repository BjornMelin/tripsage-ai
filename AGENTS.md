# Repository Guidelines

## Project Structure & Module Organization

See [docs/architecture/project-structure.md](docs/architecture/project-structure.md) for project structure details.

**Key Guidelines:**

- `tripsage/api/` hosts the FastAPI application entry point and core API logic.
- `tripsage_core/` holds domain services, models, and shared exceptions—extend logic here, not in API layers. Services are split into `business/` and `infrastructure/` subdirectories.
- `frontend/src/` is the Next.js 16 workspace with `app/`, `components/`, `lib/`, `hooks/`, `contexts/`, `stores/`, `types/`, and `schemas/` directories.
- `tests/` splits into `unit/`, `integration/`, `e2e/`, `performance/`, and `security/`; fixtures live in `tests/fixtures/` and `tests/factories/`.
- Supporting automation sits in `scripts/` and `docker/`; configuration samples ship with `.env.example`.

**Key Files:**

- Backend: `tripsage/api/routers/`, `tripsage_core/services/`, `tripsage_core/models/`, `tripsage_core/exceptions.py`
- Frontend: `frontend/src/app/api/`, `frontend/src/lib/providers/registry.ts`, `frontend/src/lib/tools/`, `frontend/src/components/ai-elements/`
- Config: `pyproject.toml`, `frontend/package.json`, `frontend/biome.json`, `.pre-commit-config.yaml`

**BYOK routes must stay server-only and fully dynamic: add `import "server-only";` plus `export const dynamic = "force-dynamic"` (no `'use cache'`) whenever secrets or per-user keys are served.**

## Tech Stack & Versions

See `pyproject.toml` and `frontend/package.json` for canonical versions.

**Backend:** Python 3.13+, FastAPI, SQLAlchemy async, Supabase, Pydantic

**Frontend:**

- Next.js `16.0.1`; React `19.2.0`
- AI SDK core `ai@6.0.0-beta.99`; UI hooks `@ai-sdk/react@3.0.0-beta.99`
- Providers: `@ai-sdk/openai@3.0.0-beta.57`, `@ai-sdk/anthropic@3.0.0-beta.53`
- Data/Auth: `@supabase/ssr@0.7.0`, `@supabase/supabase-js@2.76.1`
- Ratelimit & cache: `@upstash/ratelimit@2.0.7`, `@upstash/redis@1.35.6`, `@upstash/qstash@2.8.4`
- Styling: Tailwind CSS v4, Biome `2.3.4`, Vitest `4.0.8`

## Build, Test, and Development Commands

### Bootstrap

- Python: `uv sync --all-extras`
- Frontend: `cd frontend && pnpm install`

### Run Services

- API: `uv run python -m tripsage.api.main` (port 8000)
- Frontend: `cd frontend && pnpm dev` (port 3000)
- Containers: `docker-compose up --build`

### Testing

- Backend: `uv run pytest --cov=tripsage --cov=tripsage_core` (≥90% coverage)
- Frontend: `pnpm test:run` (target ≥85% coverage), `pnpm test:e2e` (Playwright)

See Quality Gates section for formatting/linting commands. For file-scoped commands, see respective config files.

## Coding Style & Naming Conventions

### Python Style Guide

- Type hints: Required; use modern Python 3.9+ syntax (`list[...]`, `dict[...]`, `X | None`).
- Docstrings: Google-style with `Args:`, `Returns:`, `Raises:` sections. See [docs/developers/code-standards.md](docs/developers/code-standards.md) for examples.
- Line length: 88 characters (enforced via Ruff).
- Async-first: Use `async`/`await` for all I/O operations.
- Exceptions: Derive from `CoreTripSageError` (`tripsage_core.exceptions`).
- Naming: `snake_case` functions/variables, `PascalCase` classes, `UPPER_CASE` constants.

### TypeScript Style Guide

- Follow Google's TypeScript Style Guide; enforce with Biome.
- File headers: `@fileoverview` only when it adds value.
- File order: `@fileoverview` → blank line → `"use client"` (where needed) → blank line → imports → implementation.
- JSDoc/TSDoc: Use `/** ... */` for user-facing docs; `//` for implementation notes.
- JSDoc formatting: Markdown; tags on separate lines; wrap `@param`/`@return` text indented by four spaces.
- Naming: PascalCase for components/hooks in `frontend/app`, camelCase for utilities in `frontend/lib`.
- Type safety: Strict mode; avoid `any`; handle null/undefined.

### Biome Configuration

- Single gate: `pnpm biome:check` (fail on warnings), `pnpm biome:fix`, `pnpm format:biome`.
- See `frontend/biome.json` for configuration. Do not change unless explicitly requested.

### Formatting

- Python: Automated via Ruff (`ruff format .`). Never hand-format generated OpenAPI clients—regenerate instead.
- TypeScript: Automated via Biome (`pnpm biome:fix`). Never hand-format generated code.

## Library and Design Principles

- Library-first: Prefer maintained libraries that cover ≥80% needs with ≤30% custom code. Use AI SDK v6 primitives (streaming, tools, structured outputs) instead of bespoke orchestrators.
- KISS/DRY/YAGNI: Keep solutions straightforward; avoid clever abstractions unless required. Aggressively remove duplication. Implement only what's needed now.
- Keep adapters thin; handlers/services cohesive. Avoid wrapping AI SDK streaming.
- Share Zod v4+ schemas via `src/schemas`; don't duplicate types between client/server.
- Common pitfalls: Don't re-implement streaming/tool calling (use AI SDK v6); don't duplicate Zod types; avoid module-scope clients/ratelimiters in Route Handlers—build inside requests.

## Frontend Development

When working on files under `frontend/`, follow these instructions which supersede general guidelines where specified.

### Ground Rules

- Library-first, KISS/DRY/YAGNI: See Library and Design Principles section.
- Repo gates: Biome formatting+linting, `tsc --noEmit`, and targeted Vitest. Treat warnings as failures.
- IDs & timestamps: Use `@/lib/security/random` (`secureUUID`, `secureId`, `nowIso`). Do not use `Math.random` or direct `crypto.randomUUID`.
- Auth & caching: Next 16 `cacheComponents: true` enabled; do not publicly cache auth-dependent responses. Keep Supabase cookie reads in server contexts only.
- Evidence & safety: Follow primary docs; don't echo secrets; no client-side env usage for server keys.

### Models and Providers

#### Vercel AI Gateway (Primary)

- Primary routing layer for multi-provider support, observability, fallbacks, metrics, and budgets.
- Users provide their own provider API keys (OpenAI, Anthropic, xAI, Gemini, etc.) which are routed through Gateway.
- Configure via `createGateway({ baseURL: "https://ai-gateway.vercel.sh/v1", apiKey: process.env.AI_GATEWAY_API_KEY })` from the `ai` package (v6).
- Users can also use their own provider keys directly through Gateway without a Gateway API key; billing goes to their provider accounts.
- Primary docs: vercel.com/docs/ai-gateway (OpenAI-compatible API).

#### BYOK Provider Registry (Alternative)

- Source: `frontend/src/lib/providers/registry.ts:1`.
- Direct provider resolution without Gateway; use when Gateway is unavailable or not desired.
- Resolves user-specific keys server-side and returns a ready `LanguageModel` for AI SDK v6.
- Supported providers: `openai`, `openrouter`, `anthropic`, `xai` (OpenAI-compatible for xAI).
- OpenRouter uses the OpenAI provider configured with `baseURL: "https://openrouter.ai/api/v1"` (OpenAI‑compatible). No attribution headers.
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

**Note:** When using Gateway, keep a single routing path (either Gateway or BYOK registry) for simplicity; don't mix per-route.

### AI SDK v6 Patterns

#### Streaming Route with Tools

Use Next.js Route Handlers; keep side-effects in the adapter; define tools with Zod; stream tokens. Return `result.toUIMessageStreamResponse()` for compatibility with `@ai-sdk/react` UI.

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

For structured JSON without tools, use `generateObject`/`streamObject` with Zod. See `frontend/src/app/api/ai/stream/route.ts:1` for examples.

**Key points:** Always convert UI messages server-side with `convertToModelMessages(messages)`. Token budgeting: see `frontend/src/app/api/chat/_handler.ts:1` for helpers. Docs: ai-sdk.dev.

### Client UI

- Hooks: `useChat` from `@ai-sdk/react` manages chat state and streaming.
- Transport: prefer `DefaultChatTransport` with `api: "/api/chat/stream"` for resumable streams.
- UI primitives: `src/components/ai-elements/*` (Message, Response, PromptInput, Sources, etc.).
- Reference: `frontend/src/app/chat/page.tsx:1` shows end-to-end usage.

### Next.js 16 Caching and Supabase SSR

- Caching: `cacheComponents: true` enabled. Use `'use cache'` for file/component caching; `'use cache: private'` for user-specific data. Use `cacheTag()` and `revalidateTag(tag)` for invalidation. Avoid public caching for routes that read/set cookies.
- Prefetch: Next auto-prefetches `next/link` in viewport. Keep links minimal and meaningful.
- Supabase SSR: Server client factory `frontend/src/lib/supabase/server.ts:1`; middleware `frontend/middleware.ts:1` refreshes sessions. Never access Supabase cookies in client components.

Docs: Next.js caching guide, Supabase SSR docs.

### Next.js Performance Optimizations

- Fonts: use `next/font` to self-host fonts; prefer variable fonts and minimal subsets.
- Images: use `next/image` with proper `sizes`, `priority` for LCP images, `placeholder="blur"`.
- Code splitting: keep most components as Server Components; mark Client Components only where interaction is needed.
- Dynamic import: use `next/dynamic` for heavy Client Components; consider `ssr: false` only for browser-only dependencies.
- Compiler: `reactCompiler: true` enabled. Keep components pure; prefer stable references.

Docs: Next.js image/font optimization, React Compiler intro.

### Rate Limiting and Ephemeral State

- Use `@upstash/ratelimit` + `@upstash/redis`. Initialize inside the request adapter (not module scope). Prefer `Redis.fromEnv()`.
- Examples: `frontend/src/app/api/chat/route.ts:1` and stream routes under `frontend/src/app/api/**/route.ts`.

Docs: Upstash ratelimit examples.

### Styling and UI System

- Tailwind v4 with `@tailwindcss/postcss`; import via `@import "tailwindcss";` (see `frontend/postcss.config.mjs:1` and `frontend/src/app/globals.css:1`).
- CSS custom properties (`@layer base`) for theming; Tailwind v4 `@theme` tokens optional.
- shadcn configured via `frontend/components.json:1` with `rsc: true` and `cssVariables: true`.

Docs: Tailwind v4 functions & directives, shadcn UI.

### React 19 Guidance

- React Compiler: Enabled via `reactCompiler: true`. Automatically optimizes re-renders. Keep components pure; prefer stable references.
- Data fetching: Prefer Server Components and Route Handlers/Server Actions. Avoid `useEffect` for server-fetchable data. Use Suspense boundaries for slow UI.
- Actions: Use `useActionState` for form actions; `useOptimistic` for immediate UI feedback.

Docs: React Compiler intro, `useActionState`, `useOptimistic`.

### Frontend Checklists

- Server routes: Next Route Handler; DI resolver for model; `streamText`; Upstash limit inside request; `toUIMessageStreamResponse()`. No module-scope state; typed inputs; explicit 4xx on validation errors.
- Client: `useChat` with `DefaultChatTransport` to `/api/chat/stream`; local `ai-elements/*` components; no secrets.
- Schemas: Share Zod via `src/schemas`; avoid duplication.
- Tests: Targeted Vitest runs; no network; mock AI SDK/Upstash/Supabase at adapter boundary.
- Style: Biome clean; TypeScript strict; minimal JSDoc (no duplicate types).

## Testing Guidelines

### Backend Testing

- Name tests `test_*.py`; group under matching package path (e.g., `tests/unit/api/test_trips.py`).
- Keep fixtures declarative in `tests/fixtures/`; prefer factory helpers over hardcoded JSON.
- Coverage target: ≥90% (CI enforced). See [docs/developers/development-guide.md](docs/developers/development-guide.md) for details.

**Test Structure:**

```text
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for API endpoints
├── e2e/           # End-to-end tests
├── performance/   # Performance and load tests
├── security/      # Security tests
├── fixtures/      # Test fixtures and data
└── factories/     # Factory helpers for test data
```

### Frontend Testing

- Framework: Vitest with jsdom default, V8 coverage. Config at `frontend/vitest.config.ts:1`.
- Coverage thresholds: lines 90, statements 90, functions 90, branches 85. Coverage target: ≥85%.
- Global setup: `frontend/src/test-setup.ts:1` wires mocks (Next navigation/router, Supabase, toast hooks, storage, etc.).
- No real network calls. Mock `streamText`, provider factories, Supabase, and Upstash at adapter boundary.
- Commands:
  - Local: `cd frontend && pnpm test:run` for full suite, or `pnpm test` for watch/dev.
  - CI: `cd frontend && pnpm test:ci` uses sharded `vitest run` invocations with constrained workers to avoid jsdom/V8 heap pressure.
- See tests under `frontend/src/app/api/**/__tests__` and `frontend/src/lib/**/__tests__`.

## Quality & Documentation Gates

### Python Quality Gates

- Format: `ruff format .`
- Lint: `ruff check . --fix`
- Type check: `uv run pyright`
- Tests: `uv run pytest --cov=tripsage --cov=tripsage_core` (≥90% coverage)

### TypeScript Quality Gates

- Format/lint: `pnpm biome:check` (fail on warnings), `pnpm biome:fix`
- Type check: `pnpm type-check`
- Tests: `pnpm test:run` (≥85% coverage)

CI enforces all gates; pre-commit runs a fast subset (see `.pre-commit-config.yaml`).

### Documentation Requirements

- **Python**: Google-style docstrings with `Args:`, `Returns:`, `Raises:` sections. See [docs/developers/code-standards.md](docs/developers/code-standards.md) for examples.
- **TypeScript**: JSDoc/TSDoc for top-level exports and non-obvious functions. Use `//` for implementation notes, `/** ... */` for user-facing docs.

## Commit & Pull Request Guidelines

- Use Conventional Commit messages with scope: `feat(scope):`, `fix(scope):`, `chore(scope):`, etc. (e.g., `feat(cache): add Redis caching layer`)
- Keep commits atomic; prefer checkpoints (`feat: …`, `test: …`).
- Before opening PR, ensure lint, type, and test gates pass.
- PRs must describe scope and list validation commands.

## Security & Configuration Tips

- Never commit secrets; copy from `.env.example` and store overrides in your `.env`.
- Verify platform connectivity with `uv run python scripts/verification/verify_connection.py` and related checks before pushing.
- Do not expose secrets in prompts, logs, or client code. Never echo `process.env` values.
- Keep provider keys server-side (BYOK registry). When using Gateway, use the Gateway API key, not raw provider keys, on the server only.
- Do not public-cache responses that read or set cookies.

## Tool Calling & Workflows

### Research & Information Gathering

- **Library/API research**: `exa.get_code_context_exa` → `firecrawl.firecrawl_search` → `exa.crawling_exa` (specific URLs)
- **Web research**: `exa.web_search_exa` for quick facts; `firecrawl.firecrawl_search` with deep research parameters for comprehensive multi-source research
- **Single page extraction**: `firecrawl.firecrawl_scrape` for known URLs

### Code Analysis & Review

- **Architecture assessment**: `zen.analyze` for codebase structure, patterns, and scalability
- **Systematic code review**: `zen.codereview` for quality, security, and best practices
- **Security audit**: `zen.secaudit` for security vulnerabilities and compliance

### Planning & Decision Making

- **Task decomposition**: `zen.planner` for complex features/refactors; maintain plan via `update_plan` (single `in_progress` task)
- **Deep investigation**: `zen.thinkdeep` for complex bugs, performance issues, or architecture decisions
- **Multi-model consensus**: `zen.consensus` for contested choices; applies decision framework (Solution Leverage 35%, Application Value 30%, Maintenance Load 25%, Adaptability 10%)

## Useful Documentation References

- AI SDK v6: <https://ai-sdk.dev>
- Next.js: Cache Components, caching guide, image/font optimization, React Compiler
- React: Compiler intro, `useActionState`, `useOptimistic`
- Supabase SSR: <https://supabase.com/docs/guides/auth/server-side/creating-a-client>
- Tailwind v4: Functions & directives, v4 blog
- Vercel AI Gateway: <https://vercel.com/docs/ai-gateway/openai-compat>
- Upstash ratelimit: <https://vercel.com/templates/next.js/ratelimit-with-upstash-redis>
- shadcn UI: <https://ui.shadcn.com>
