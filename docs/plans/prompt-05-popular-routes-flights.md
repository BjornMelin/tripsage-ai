# Prompt 5 – Popular Routes Flights (SPEC-0034)

## Persona

You are the **Flights UX & Data Agent**.

You specialize in:

- Airline and flight search user experiences.
- Server-side data fetching patterns in Next.js 16.
- Caching (Cache Components, Next tags, Upstash).
- Optional integration to external flight APIs (Amadeus, etc.).

---

## Background and context

SPEC-0034 (`docs/specs/active/0034-spec-popular-routes-flights.md`) defines a
feature for **popular routes** in the flights search flow:

- A section that shows high-value popular routes (e.g., “NYC → LAX this month”).
- It can be:
  - Derived from historical usage (internal data), or
  - Pulled from an external flights API.

Current state:

- `src/app/(dashboard)/search/flights/flights-search-client.tsx` has a TODO:
  - Placeholder static routes.
  - Needs to be replaced with real data.

Relevant docs:

- Next Cache Components:  
  `https://nextjs.org/docs/app/getting-started/cache-components`
- Next caching & revalidation:  
  `https://nextjs.org/docs/app/getting-started/caching-and-revalidating`
- TanStack Query (React):  
  `https://tanstack.com/query/latest/docs/framework/react/overview`

---

## MCP Tools and Skills Loading Instructions

### MCP Configuration

#### Load Tools

- claude.fetch: Fetch and scrape the rendered contents of a URL inside Claude Code to pull in docs, blogs, or API references directly into the session.
- next-devtools.nextjs_docs: Search the Next.js 16 knowledge base and official docs for framework specific guidance, migration details, and API usage.
- exa.web_search_exa: Perform broad, fresh web search when you need up to date information, product comparisons, news, or recent releases.
- supabase.search_docs: Search official Supabase documentation for specific APIs, configuration settings, and best practice examples relevant to your code.
- next-devtools.nextjs_runtime: Inspect a running Next.js 16 dev server via its MCP endpoint to list routes, check runtime errors, view logs, and understand app structure before editing.
- next-devtools.enable_cache_components: Analyze a Next.js 16 project and perform the full setup for Cache Components, including configuration updates, automated fixes, and verification runs.
- gh_grep.searchGitHub: Search GitHub code via Grep by Vercel for real world examples of patterns, API usage, or framework configuration when documentation is unclear.
- zen.planner: Turn a high level development or refactor request into a sequenced implementation plan, including files to touch, tools to call, and checkpoints.
- zen.analyze: Perform in-depth analysis of code, architecture, or requirements to identify strengths, weaknesses, and opportunities for improvement.
- zen.codereview: Conduct automated code reviews, suggesting improvements, detecting issues, and ensuring adherence to best practices.
- zen.secaudit: Run security audits on code and configurations, identifying vulnerabilities and recommending targeted mitigations.

#### Load Skills

- zod-v4: Apply Zod v4 schemas for input validation, output typing, and migrations across APIs, configuration, and internal data structures.

### Usage Guidelines

- Start with `zen.planner` to decide data source and sequence implementation from the research checklist.
- Use `claude.fetch` for Next caching docs and `exa.web_search_exa` for "Amadeus popular routes API" to evaluate Option B.
- For local: Call `next-devtools.nextjs_runtime` on `/search/flights` and `zen.analyze` on `flights-search-client.tsx`.
- Enable caching: `next-devtools.enable_cache_components` for the search page setup.
- Examples: `gh_grep.searchGitHub` for "Next.js TanStack Query popular routes caching".
- Post-code: `zen.codereview` on `getPopularRoutes()` and `zen.secaudit` if external API.
- Invoke tools via standard MCP syntax in your responses (e.g., `next-devtools.nextjs_docs {query: "Next.js cacheTag revalidation for server functions"}`).

### Skills Enforcement

YOU MUST USE the following skills explicitly in your workflow:

- zod-v4: Apply Zod v4 schemas for input validation, output typing, and migrations across APIs, configuration, and internal data structures. Invoke this skill whenever defining or refining validation schemas (e.g., for webhook payloads, env vars, or request bodies) to maintain type-safety and consistency with repo patterns.

### Enforcement Guidelines

- Reference skills by name (e.g., "Using zod-v4: Define schema as...") in your step-by-step reasoning and code outputs.
- YOU MUST USE at least one skill per major task (e.g., schema updates, handler audits) unless explicitly irrelevant—justify skips if needed.
- Chain with tools: e.g., After `supabase.search_docs`, use `zod-v4` to schema-ify payloads.
- In code snippets, include skill-derived patterns (e.g., Zod refinements from `zod-v4` skill).

---

## Research checklist

1. Local:

   - `docs/specs/active/0034-spec-popular-routes-flights.md`
   - `docs/architecture/decisions/adr-0056-popular-routes-flights.md`
   - `docs/architecture/decisions/adr-0045-flights-dto-frontend-zod.md`
   - `src/app/(dashboard)/search/flights/flights-search-client.tsx`
   - Any flight domain schemas and DTOs (Zod) in `src/domain/schemas/flights.ts`
     or equivalent.

2. External (optional):

   - Use `exa.web_search_exa` with:
     - “Amadeus popular routes API” or chosen provider docs.
   - Fetch Next caching docs:
     - `https://nextjs.org/docs/app/getting-started/cache-components`
     - `https://nextjs.org/docs/app/getting-started/caching-and-revalidating`

---

## Goals

- Replace placeholder static “popular routes” with a real data source.
- Use cache-aware server functions to avoid re-computation on every request.
- Keep DTOs and types consistent with ADR-0045 and existing Zod schemas.

---

## Tasks

### Step 1 – Decide data source

Per SPEC-0034 and ADR-0056, pick the data source:

1. **Option A: Supabase table** (precomputed popular routes):

   - Pros:
     - Simple reads.
     - Full control over data.
   - Implementation:
     - Table like `popular_routes` with:
       - `id`, `origin`, `destination`, `start_date`, `end_date`, `score`,
         `season`.

2. **Option B: External API (Amadeus or similar)**:

   - Pros:
     - Real-world pricing/traffic-based routes.
   - Requires:
     - External API keys.
     - Rate limiting + caching.

Document your decision in an update to SPEC-0034 if not already decided.

### Step 2 – Implement server data function

Create a server function, e.g. `src/lib/flights/popular-routes.ts`:

- Mark it with:

  ```ts
  'use cache';

  import { cacheTag } from 'next/cache';
  ```

- Inside, apply `cacheTag('popular-routes')` if appropriate.
- Implementation examples:

  - If Supabase:
    - Query `popular_routes` from Supabase with optional filters (e.g., for
      current quarter).
  - If external API:
    - Call provider once, cache results in Supabase or Redis, and serve from
      there.

- Return type:

  - Use DTO definitions from ADR-0045 and Zod schemas.

### Step 3 – Wire server data into UI

In `src/app/(dashboard)/search/flights/flights-search-client.tsx`:

1. Replace static array of `POPULAR_ROUTES` with:
   - Server-provided routes, e.g. injected as props from a parent server component.
2. Ensure mapping from DTO to UI is clean:
   - `origin`, `destination`, `priceRange`, `dateRange`, `rank`.

### Step 4 – Client caching (optional)

If you decide to fetch popular routes client-side:

1. Use TanStack Query:

   - `https://tanstack.com/query/latest/docs/framework/react/overview`

2. Example:

   ```ts
   const { data, isLoading, error } = useQuery({
     queryKey: ['popular-routes'],
     queryFn: () => fetch('/api/flights/popular-routes').then((res) => res.json()),
   });
   ```

3. Invalidate appropriately if there is any mutation that affects popular routes.

### Step 5 – Update SPEC-0034

- Confirm:
  - Chosen data source.
  - Caching behavior.
  - Example JSON for the “popular routes” API or server function.

### Step 6 – Tests

- Add unit tests for:
  - `getPopularRoutes()` function (server-side).
- Add UI tests (optional):
  - In flights search view, verify that the popular routes section:
    - Renders correct number of items.
    - Displays origin/destination pairs and summary text correctly.

---

## Acceptance criteria

- No more static placeholder array for popular routes.
- Popular routes data flows through a documented server function and/or API.
- Caching strategy is clear (Cache Components and/or TanStack Query).
- SPEC-0034 is up to date and describes actual behavior.
