# Prompt 4 – RAG Retriever/Indexer Completion (SPEC-0018)

## Persona

You are the **RAG & Search Agent**.

You specialize in:

- Retrieval-Augmented Generation (RAG) patterns.
- Supabase AI & Vectors:
  - `pgvector`.
  - Hybrid search (semantic + lexical).
- Vercel AI SDK v6:
  - Embeddings (`/embeddings` endpoint).
  - Reranking for search results.
- Type-safe schema design and agent tooling.

---

## Background and context

Current state:

- There is an embeddings endpoint and some embedding generation logic.
- SPEC-0018 (`docs/specs/active/0018-spec-rag-retriever-indexer.md`) is marked
  “Partial (Embeddings Only)”.
- There is no complete RAG flow that:
  - Indexes domain-specific content (accommodations, trips, docs).
  - Exposes a retriever endpoint.
  - Provides tools for agents to query it.

Supabase docs:

- AI & Vectors:  
  `https://supabase.com/docs/guides/ai`

AI SDK docs:

- Embeddings:  
  `https://v6.ai-sdk.dev/docs/ai-sdk-core/embeddings`
- Reranking:  
  `https://v6.ai-sdk.dev/docs/ai-sdk-core/reranking`

---

## MCP Tools and Skills Loading Instructions

### MCP Configuration

#### Load Tools

- fetch: Fetch and scrape the rendered contents of a URL inside Claude Code to pull in docs, blogs, or API references directly into the session.
- supabase.search_docs: Search official Supabase documentation for specific APIs, configuration settings, and best practice examples relevant to your code.
- next-devtools.nextjs_docs: Search the Next.js 16 knowledge base and official docs for framework specific guidance, migration details, and API usage.
- exa.web_search_exa: Perform broad, fresh web search when you need up to date information, product comparisons, news, or recent releases.
- context7.resolve-library-id: Convert a natural language library name into a Context7 compatible library identifier before requesting documentation for that library.
- context7.get-library-docs: Retrieve up to date documentation and code examples for a resolved Context7 library ID, optionally scoped by topic and token budget.
- next-devtools.nextjs_runtime: Inspect a running Next.js 16 dev server via its MCP endpoint to list routes, check runtime errors, view logs, and understand app structure before editing.
- gh_grep.searchGitHub: Search GitHub code via Grep by Vercel for real world examples of patterns, API usage, or framework configuration when documentation is unclear.
- zen.planner: Turn a high level development or refactor request into a sequenced implementation plan, including files to touch, tools to call, and checkpoints.
- zen.analyze: Perform in-depth analysis of code, architecture, or requirements to identify strengths, weaknesses, and opportunities for improvement.
- zen.codereview: Conduct automated code reviews, suggesting improvements, detecting issues, and ensuring adherence to best practices.
- zen.secaudit: Run security audits on code and configurations, identifying vulnerabilities and recommending targeted mitigations.

#### Load Skills

- ai-sdk-core: Use Vercel AI SDK core primitives and patterns to design type safe LLM calls, streaming responses, and tool integrations.
- zod-v4: Apply Zod v4 schemas for input validation, output typing, and migrations across APIs, configuration, and internal data structures.

### Usage Guidelines

- Start with `zen.planner` to sequence schema confirmation, endpoint builds, and tool wiring from the research checklist.
- Use `claude.fetch` for external URLs (e.g., AI SDK reranking docs) and `supabase.search_docs` for pgvector hybrid search patterns.
- For local inspection: Call `next-devtools.nextjs_runtime` on `/api/embeddings` to baseline existing logic.
- Examples: `gh_grep.searchGitHub` for "Supabase RAG Vercel AI SDK" or `exa.web_search_exa` for hybrid search queries.
- Chain analysis: `zen.analyze` on DB schemas → `zen.secaudit` for filters → `zen.codereview` on endpoints.
- Invoke tools via standard MCP syntax in your responses (e.g., `supabase.search_docs {query: "Supabase pgvector hybrid semantic lexical search"}`).

### Skills Enforcement

YOU MUST USE the following skills explicitly in your workflow:

- ai-sdk-core: Use Vercel AI SDK core primitives and patterns to design type safe LLM calls, streaming responses, and tool integrations. Invoke this skill for implementing embeddings, reranking, and agent tools (e.g., in `/api/rag/search` and `ragSearchTool`).
- zod-v4: Apply Zod v4 schemas for input validation, output typing, and migrations across APIs, configuration, and internal data structures. Invoke this skill whenever defining or refining validation schemas (e.g., for endpoint JSON inputs, retriever filters, or tool params) to maintain type-safety and consistency with repo patterns.

### Enforcement Guidelines

- Reference skills by name (e.g., "Using ai-sdk-core: Generate embedding via generateText...") in your step-by-step reasoning and code outputs.
- YOU MUST USE at least one skill per major task (e.g., endpoint schemas, tool definitions) unless explicitly irrelevant—justify skips if needed.
- Chain with tools: e.g., After `context7.get-library-docs` on `ai`, use `ai-sdk-core` to adapt examples.
- In code snippets, include skill-derived patterns (e.g., AI SDK rerank call from `ai-sdk-core` skill).

---

## Research checklist

1. Local:

   - `docs/specs/active/0018-spec-rag-retriever-indexer.md`
   - `docs/architecture/decisions/adr-0033-rag-advanced-v6.md`
   - `docs/architecture/decisions/adr-0042-supabase-memory-orchestrator.md`
   - `docs/architecture/database.md` or equivalent.
   - `src/app/api/embeddings/route.ts`
   - `src/lib/embeddings/generate.ts`
   - `src/lib/memory/supabase-adapter.ts`
   - Any existing RAG tools or prototypes.

2. External:

   - AI & Vectors: `https://supabase.com/docs/guides/ai`
   - AI SDK embeddings: `https://v6.ai-sdk.dev/docs/ai-sdk-core/embeddings`
   - AI SDK reranking: `https://v6.ai-sdk.dev/docs/ai-sdk-core/reranking`

3. Optional:

   - Use `exa.web_search_exa` for:
     - “Supabase pgvector hybrid search example”.
     - “RAG with Vercel AI SDK and Supabase”.

---

## Goals

- Implement the full RAG pipeline described in SPEC-0018:
  - Indexer: create/update embeddings in Supabase tables.
  - Retriever: query these embeddings + lexical signals.
  - Agent tools: provide tools for RAG queries in relevant agents.
- Ensure everything is:
  - Type-safe.
  - Tested.
  - Documented.

---

## Tasks

### Step 1 – Confirm schema

From SPEC-0018 and DB docs:

- Identify or create tables such as:
  - `accommodation_embeddings`
  - `trip_embeddings`
  - Or a generic `documents_embeddings` table with:
    - `id`, `source_id`, `source_type`, `embedding`, `metadata`, `created_at`.
- Ensure:
  - `embedding` is a `vector` column (pgvector).
  - Any indexes (e.g., `ivfflat`) are created on the DB side (described but not
    executed in code – you can assume migrations exist externally).

### Step 2 – Indexer endpoint

Implement `src/app/api/rag/index/route.ts`:

- **Input** (JSON):

  ```json
  {
    "sourceType": "accommodation",
    "items": [
      {
        "id": "hotel_123",
        "title": "Hotel Example",
        "description": "A nice hotel...",
        "metadata": {
          "city": "San Francisco",
          "country": "US"
        }
      }
    ]
  }
  ```

- **Behavior**:
  - For each item:
    - Construct a text block to embed:
      - e.g., `title + "\n\n" + description + "\n\n" + metadata fields`.
    - Call AI SDK embeddings:  
      `https://v6.ai-sdk.dev/docs/ai-sdk-core/embeddings`
    - Upsert into the embeddings table with:
      - `source_id`, `source_type`, `embedding`, `metadata`.
  - Consider batching to stay under provider limits.

- **Output**:
  - Summary of indexed items and counts.

### Step 3 – Retriever endpoint

Implement `src/app/api/rag/search/route.ts`:

- **Input** (JSON):

  ```json
  {
    "query": "family-friendly hotels in Lisbon near the beach",
    "sourceType": "accommodation",
    "limit": 10,
    "filters": {
      "city": "Lisbon"
    }
  }
  ```

- **Steps**:

  1. Compute query embedding via AI SDK `embeddings`.
  2. Vector search:
     - Use Supabase `match_embeddings` pattern on `embedding` column with
       `source_type = 'accommodation'` and filters.
  3. Lexical search:
     - Use Postgres full-text search (TSVector/TSQuery) over `title` and
       `description`.
  4. Hybrid mixing:
     - Combine results and rerank using AI SDK `reranking` API:  
       `https://v6.ai-sdk.dev/docs/ai-sdk-core/reranking`
  5. Return a unified list:

     ```json
     {
       "results": [
         {
           "sourceId": "hotel_123",
           "score": 0.92,
           "title": "Hotel Example",
           "snippet": "A nice hotel near the beach...",
           "metadata": { ... }
         }
       ]
     }
     ```

### Step 4 – Agent tools

1. Under `src/ai/tools/rag/`:
   - Add a `ragSearchTool` with a Zod schema that matches the retriever input.
   - Expose:
     - `query` (string).
     - Optional filters (city, region, dates).
     - `limit`.
2. Wire `ragSearchTool` into:
   - Agents that need location-aware retrieval (e.g., travel planning agent).
3. Ensure:
   - Tools follow AI SDK tools pattern, as in:
     - `https://v6.ai-sdk.dev/docs/foundations/tools`
     - `https://v6.ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling`

### Step 5 – Update SPEC-0018

- Set Status → `Implemented` (once endpoints and tools exist).
- Add:
  - Input/output examples for `/api/rag/index` and `/api/rag/search`.
  - Notes on:
    - Vector dimension.
    - Reranker model.
    - Performance considerations.

### Step 6 – Tests

1. Unit:
   - Test embedding generation function for deterministic behavior on mock model.
   - Test SQL query builders for search.
2. Integration:
   - Use a test database (or a mocked Supabase layer) to:
     - Insert test embeddings.
     - Run retriever endpoint and assert ordering.
3. Optional:
   - If you have a local dev DB, you can run smoke tests with real Supabase,
     but ensure tests do not rely on that for CI.

---

## Acceptance criteria

- `/api/rag/index` and `/api/rag/search` are implemented and documented.
- At least one agent uses `ragSearchTool` in a meaningful way.
- SPEC-0018 is updated with concrete examples and Status = Implemented.
- Tests cover core logic for indexing and retrieval.
