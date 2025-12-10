# Prompt 6 – Search Personalization History (SPEC-0035)

## Persona

You are the **Search Personalization Agent**.

You specialize in:

- Low-risk personalization for search experiences.
- Supabase schema design with RLS.
- Designing logging and readback patterns for search events.

---

## Background and context

SPEC-0035 (`docs/specs/active/0035-spec-search-personalization-history.md`)
defines a feature for **search history-based personalization**:

- Capture recent searches (flights, hotels, unified).
- Use them to:
  - Pre-populate inputs.
  - Display “Recent searches” lists.
- The design emphasizes:
  - Minimal PII.
  - User-level scope (no cross-user correlations).

Supabase database docs:

- `https://supabase.com/docs/guides/database/overview`

---

## MCP Tools and Skills Loading Instructions

### MCP Configuration

#### Load Tools

- claude.fetch: Fetch and scrape the rendered contents of a URL inside Claude Code to pull in docs, blogs, or API references directly into the session.
- supabase.search_docs: Search official Supabase documentation for specific APIs, configuration settings, and best practice examples relevant to your code.
- next-devtools.nextjs_docs: Search the Next.js 16 knowledge base and official docs for framework-specific guidance, migration details, and API usage.
- exa.web_search_exa: Perform broad, fresh web search when you need up-to-date information, product comparisons, news, or recent releases.
- next-devtools.nextjs_runtime: Inspect a running Next.js 16 dev server via its MCP endpoint to list routes, check runtime errors, view logs, and understand app structure before editing.
- gh_grep.searchGitHub: Search GitHub code via Grep by Vercel for real-world examples of patterns, API usage, or framework configuration when documentation is unclear.
- zen.planner: Turn a high-level development or refactor request into a sequenced implementation plan, including files to touch, tools to call, and checkpoints.
- zen.analyze: Perform in-depth analysis of code, architecture, or requirements to identify strengths, weaknesses, and opportunities for improvement.
- zen.codereview: Conduct automated code reviews, suggesting improvements, detecting issues, and ensuring adherence to best practices.
- zen.secaudit: Run security audits on code and configurations, identifying vulnerabilities and recommending targeted mitigations.

#### Load Skills

- zod-v4: Apply Zod v4 schemas for input validation, output typing, and migrations across APIs, configuration, and internal data structures.

### Usage Guidelines

- Start with `zen.planner` to outline schema design and logging integration from the research checklist.
- Use `claude.fetch` for Supabase overview docs and `supabase.search_docs` for RLS/JSONB patterns in `search_history`.
- For local flows: Call `next-devtools.nextjs_runtime` on `/search/flights/*` to identify submit hooks.
- Examples: `gh_grep.searchGitHub` for "Next.js Supabase search history logging RLS".
- Chain security: `zen.analyze` on search params → `zen.secaudit` for PII → `zen.codereview` on helpers/UI.
- Invoke tools via standard MCP syntax in your responses (e.g., `supabase.search_docs {query: "Supabase RLS for user-specific history table"}`).

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

   - `docs/specs/active/0035-spec-search-personalization-history.md`
   - Any existing search logging or analytics modules.
   - Flight/hotel/unified search flows:
     - `src/app/(dashboard)/search/flights/*`
     - `src/app/(dashboard)/search/hotels/*`
     - `src/app/(dashboard)/search/unified/*`
   - Supabase client code for user-authenticated calls.

2. External:

   - `https://supabase.com/docs/guides/database/overview`
   - Optionally, `exa.web_search_exa` for:
     - “search history personalization patterns”.

---

## Goals

- Design and implement a `search_history` data model in Supabase.
- Log searches from flights/hotels/unified flows.
- Read and use recent history to improve UX without being intrusive.

---

## Tasks

### Step 1 – Supabase table design (schema-only)

Design a `search_history` table, defined in migrations / SQL (not executed here,
but documented):

- Columns (example):

  - `id` (PK).
  - `user_id` (FK to auth.users or your internal users table).
  - `search_type` (e.g., `'flights' | 'hotels' | 'unified'`).
  - `params` (JSONB):
    - Includes origin, destination, dates, filters, etc.
  - `created_at` (timestamptz default now()).

- RLS (described in spec, implemented externally):
  - Users can only see their own history rows.

Update SPEC-0035 with this schema in a `Schema` section.

### Step 2 – Logging searches

For each relevant search action:

1. Identify where a “search click” or “search submit” happens in code:
   - Flights search.
   - Hotels search.
   - Unified search.
2. Add server actions or API endpoints that:
   - Receive search parameters (typed with Zod).
   - Persist a row into `search_history` via Supabase.

Guidelines:

- Do not log more PII than necessary (no raw user free-text notes, etc.).
- Use typed DTOs so that `params` are consistent.

### Step 3 – Reading search history

Implement helper functions:

- `getUserSearchHistory(userId: string, limit: number = 10)`:

  - Query latest N rows from `search_history` for that user.
  - Return a normalized DTO:
    - `searchType`.
    - Derived summary (e.g., `"NYC → LAX, Jun 2025"`).
    - Raw `params`.

Wrap it in a server-side function that can be used in server components (with
`'use cache'` if appropriate).

### Step 4 – Integrate with search UIs

1. Flights search:

   - Use `getUserSearchHistory` to:
     - Show “Recent searches” list.
     - Provide quick “repeat search” buttons.

2. Hotels and unified search:

   - Same pattern, but filter by `search_type`.

3. UX choice:

   - Keep personalization subtle and opt-out friendly (if you later introduce
     settings).

### Step 5 – SPEC-0035 update

- Add:

  - “Data Model” section with table schema.
  - “API Contracts” for logging endpoint or server actions.
  - Example JSON for history entries.

- Set Status → `Implemented` once code is merged.

### Step 6 – Tests

- Unit tests:

  - For `logSearch` functions: ensure valid rows are constructed.
  - For `getUserSearchHistory`: ensure correct ordering and limit behavior.

- Integration tests:

  - If you can run against a local Supabase or test double:
    - Insert a few history records.
    - Verify UI shows them as expected in the search screens.

---

## Acceptance criteria

- `search_history` data model is defined and documented.
- Searches log entries in a consistent, minimal-PII format.
- Search UIs surface recent searches in a clear way.
- SPEC-0035 is updated and marked Implemented.
