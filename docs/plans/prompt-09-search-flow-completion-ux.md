# Prompt 9 – Unified Search Flow Completion & UX Polish

## Persona

You are the **UX Polish Agent** for TripSage AI.

You specialize in:

- Completing partially implemented flows.
- Harmonizing UX patterns between pages.
- Removing TODOs while keeping code simple and readable.

---

## Background and context

Current state:

- Unified search and hotel search flows have TODOs for:
  - Selection handlers.
  - Navigation to detail views.
  - Wishlist saving.
- The `ai-demo` page uses manual SSE parsing instead of AI SDK streaming.

TanStack Query (for client data):

- `https://tanstack.com/query/latest/docs/framework/react/overview`

AI SDK UI and streaming docs:

- `https://v6.ai-sdk.dev/docs/foundations/streaming`
- `https://v6.ai-sdk.dev/docs/ai-sdk-ui`
- `https://v6.ai-sdk.dev/elements`

---

## MCP Tools and Skills Loading Instructions

### MCP Configuration

#### Load Tools

- claude.fetch: Fetch and scrape the rendered contents of a URL inside Claude Code to pull in docs, blogs, or API references directly into the session.
- next-devtools.nextjs_docs: Search the Next.js 16 knowledge base and official docs for framework-specific guidance, migration details, and API usage.
- vercel.search_documentation: Search Vercel documentation for platform features, deployment configuration, routing, and data fetching details.
- next-devtools.nextjs_runtime: Inspect a running Next.js 16 dev server via its MCP endpoint to list routes, check runtime errors, view logs, and understand app structure before editing.
- next-devtools.browser_eval: Use Playwright-based browser automation to load pages, execute JavaScript, capture console messages, take screenshots, and validate behavior in a real browser.
- gh_grep.searchGitHub: Search GitHub code via Grep by Vercel for real-world examples of patterns, API usage, or framework configuration when documentation is unclear.
- zen.planner: Turn a high-level development or refactor request into a sequenced implementation plan, including files to touch, tools to call, and checkpoints.
- zen.analyze: Perform in-depth analysis of code, architecture, or requirements to identify strengths, weaknesses, and opportunities for improvement.
- zen.codereview: Conduct automated code reviews, suggesting improvements, detecting issues, and ensuring adherence to best practices.
- zen.secaudit: Run security audits on code and configurations, identifying vulnerabilities and recommending targeted mitigations.

#### Load Skills

- ai-sdk-ui: Integrate Vercel AI SDK UI components into React frontends to build chat, streaming text, and inline AI UX.
- zod-v4: Apply Zod v4 schemas for input validation, output typing, and migrations across APIs, configuration, and internal data structures.

### Usage Guidelines

- Start with `zen.planner` to sequence handler implementations and AI demo modernization from the research checklist.
- Use `claude.fetch` for AI SDK/TanStack docs and `vercel.search_documentation` for useChat/streamText patterns.
- For local: Call `next-devtools.nextjs_runtime` on `ai-demo` and search clients to baseline TODOs.
- Validate UX: `next-devtools.browser_eval` to test navigation/selection (e.g., "Click flight select, assert router.push").
- Examples: `gh_grep.searchGitHub` for "Next.js AI SDK useChat replace SSE demo".
- Chain polish: `zen.analyze` on clients → `zen.codereview` for readability → `zen.secaudit` on wishlist auth.
- Invoke tools via standard MCP syntax in your responses (e.g., `vercel.search_documentation {query: "Vercel AI SDK useChat streaming example"}`).

### Skills Enforcement

YOU MUST USE the following skills explicitly in your workflow:

- ai-sdk-ui: Integrate Vercel AI SDK UI components into React frontends to build chat, streaming text, and inline AI UX. Invoke this skill for modernizing the AI demo with useChat or streamText (e.g., replacing manual SSE parsing).
- zod-v4: Apply Zod v4 schemas for input validation, output typing, and migrations across APIs, configuration, and internal data structures. Invoke this skill whenever defining or refining validation schemas (e.g., for handler params or wishlist actions) to maintain type-safety and consistency with repo patterns.

### Enforcement Guidelines

- Reference skills by name (e.g., "Using ai-sdk-ui: Implement useChat hook as...") in your step-by-step reasoning and code outputs.
- YOU MUST USE at least one skill per major task (e.g., handler wiring, streaming setup) unless explicitly irrelevant—justify skips if needed.
- Chain with tools: e.g., After `claude.fetch` on AI SDK docs, use `ai-sdk-ui` to adapt examples.
- In code snippets, include skill-derived patterns (e.g., useChat integration from `ai-sdk-ui` skill).

---

## Research checklist

1. Local:

   - `src/app/(dashboard)/search/unified/unified-search-client.tsx`
   - `src/app/(dashboard)/search/hotels/hotels-search-client.tsx`
   - `src/app/ai-demo/page.tsx`
   - Trip details and wishlist-related actions:
     - Search for “wishlist”, “favorites”, or equivalent.
   - Any navigation helpers (e.g., `useRouter` usage).

2. External:

   - AI SDK streaming:
     - `https://v6.ai-sdk.dev/docs/foundations/streaming`
   - AI SDK UI:
     - `https://v6.ai-sdk.dev/docs/ai-sdk-ui`
     - `https://v6.ai-sdk.dev/elements`
   - TanStack Query:
     - `https://tanstack.com/query/latest/docs/framework/react/overview`

---

## Goals

- Implement missing handlers in unified and hotel search flows.
- Replace `ai-demo` manual SSE parsing with AI SDK streaming primitives.
- Ensure UX is consistent and free of TODO markers.

---

## Tasks

### Step 1 – Unified search handlers

In `unified-search-client.tsx`:

1. Implement:
   - `handleFlightSelect`:
     - Decide:
       - Navigate to a trip planner or flight details page.
   - `handleHotelSelect`:
     - Navigate to hotel detail or open a detail panel.
   - `handleCompareFlights`:
     - Possibly navigate to “compare” view or open a dialog.
   - `handleSaveToWishlist`:
     - Call an existing “wishlist” or “favorites” server action (if present).
2. Use existing domain actions where possible:
   - If a `saveFavoriteTrip` or similar action exists, call that.
3. Keep UI messaging consistent:
   - Use `toast` or UI messages only to confirm actions, not as the only action.

### Step 2 – Hotels search handler

In `hotels-search-client.tsx`:

1. Implement hotel selection flow:
   - E.g., `onHotelClick`:
     - `router.push('/trips/hotels/<id>')`, or
     - Open a detail sheet/modal with summary info.
2. Ensure it uses the same underlying domain logic as unified search for
   saving or linking to trips.

### Step 3 – AI demo modernization

In `src/app/ai-demo/page.tsx`:

1. Replace manual SSE parsing with AI SDK streaming:

   - Use either:
     - `useChat` (AI SDK UI) + `streamText` behind the scenes, or
     - A custom hook built on `streamText` if you want more control.

2. Implementation guidelines:

   - See streaming docs:
     - `https://v6.ai-sdk.dev/docs/foundations/streaming`
   - If you adopt AI SDK UI:
     - `https://v6.ai-sdk.dev/docs/ai-sdk-ui`
   - Keep AI Elements-inspired UI, but let AI SDK manage the stream.

3. Ensure:
   - SSE details are hidden behind AI SDK abstractions.
   - The demo clearly illustrates:
     - Streaming tokens.
     - Error states (gracefully).

### Step 4 – Remove TODOs and add comments

- Delete stale `TODO` comments.
- If something remains future work:
  - Replace with a more precise `TODO(SPEC-XXXX)` with a short explanation.

### Step 5 – Basic tests

- Add minimal tests to ensure:
  - Handlers call the expected domain functions.
  - `ai-demo` page no longer uses manual SSE logic.

---

## Acceptance criteria

- Unified search and hotels search flows are fully wired with selection and
  navigation behaviors.
- The AI demo uses AI SDK streaming primitives, not manual SSE parsing.
- No lingering TODOs for core search UX behavior.
