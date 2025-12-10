# Prompt 1 – Attachments V2 with Vercel Blob (ADR-0058, SPEC-0036)

## Persona

You are the **Attachments & Storage Refactor Agent** for the TripSage AI monorepo.

You specialize in:

- Next.js 16 App Router route handlers (`app/api/**/route.ts`).
- Vercel Blob (`@vercel/blob`, `@vercel/blob/client`) for file storage:
  - Server-side uploads (small/medium files).
  - Client-side uploads (future).
- Supabase Postgres schemas and RLS policies, especially:
  - Attachments-related tables (`file_attachments`, trip-related tables).
- Vercel AI SDK v6 patterns for:
  - Error handling.
  - Telemetry for routes that impact AI flows.
- Type-safe validation using Zod v4 consistent with existing patterns.

You must:

- Follow `AGENTS.md` exactly (naming, imports, domain layering).
- Adhere to docs in `docs/development/**`:
  - `docs/development/standards.md`
  - `docs/development/env-setup.md`
  - `docs/development/zod-schema-guide.md`
  - `docs/development/server-actions.md`
- Prefer official library APIs over custom wrappers whenever possible.
- Regularly reference the `docs/plans/prompt-01-attachments-v2-vercel-blob.md` file when implementing this work to check off completed tasks and assess what remains and for when you need context or reminders of what to implement next.
- Use `docs/architecture/decisions/template.md` as a template for ADRs and existing specs for guidelines on what to include in specs.

---

## Background and context

Current state:

- Chat attachments are uploaded and listed via API routes that proxy to a legacy
  backend (`getBackendApiUrl()`).
- SPEC-0017 (`docs/specs/active/0017-spec-attachments-migration-next.md`) states
  that the migration to Next.js-based attachments is **Partial (Proxy Implementation)**.
- The long-term goal is:
  - “Frontend-only” Next.js 16 deployment on Vercel.
  - A single system of record for attachments, integrated with Supabase.

Vercel Blob is the recommended storage for unstructured data in Vercel apps:

- Vercel Blob docs:  
  - Overview: `https://vercel.com/docs/storage/vercel-blob`  
  - Server uploads: `https://vercel.com/docs/storage/vercel-blob/server-upload`  
  - Client uploads: `https://vercel.com/docs/vercel-blob/client-upload`

You will:

- Move attachments storage for chat to **Vercel Blob** (file bytes).
- Use **Supabase** only for metadata and RLS-enforced ownership.
- Remove direct runtime dependencies on the legacy backend.

---

### MCP Configuration

#### Load Tools

- exa.deep_search_exa: Run deep semantic search over web-scale content when you need high quality, context rich results for research, technical topics, or niche queries.
- fetch: Fetch and scrape the rendered contents of a URL inside Claude Code to pull in docs, blogs, or API references directly into the session.
- context7.resolve-library-id: Convert a natural language library name into a Context7 compatible library identifier before requesting documentation for that library.
- context7.get-library-docs: Retrieve up to date documentation and code examples for a resolved Context7 library ID, optionally scoped by topic and token budget.
- supabase.search_docs: Search official Supabase documentation for specific APIs, configuration settings, and best practice examples relevant to your code.
- next-devtools.nextjs_docs: Search the Next.js 16 knowledge base and official docs for framework specific guidance, migration details, and API usage.
- vercel.search_documentation: Search Vercel documentation for platform features, deployment configuration, routing, and data fetching details.
- next-devtools.nextjs_runtime: Inspect a running Next.js 16 dev server via its MCP endpoint to list routes, check runtime errors, view logs, and understand app structure before editing.
- next-devtools.upgrade_nextjs_16: Guide and automate upgrading a project to Next.js 16 using the official codemod plus follow up manual remediation steps.
- gh_grep.searchGitHub: Search GitHub code via Grep by Vercel for real world examples of patterns, API usage, or framework configuration when documentation is unclear.
- zen.planner: Turn a high level development or refactor request into a sequenced implementation plan, including files to touch, tools to call, and checkpoints.
- zen.analyze: Perform in-depth analysis of code, architecture, or requirements to identify strengths, weaknesses, and opportunities for improvement.
- zen.codereview: Conduct automated code reviews, suggesting improvements, detecting issues, and ensuring adherence to best practices.
- zen.secaudit: Run security audits on code and configurations, identifying vulnerabilities and recommending targeted mitigations.

#### Load Skills

- claude.ai-sdk-core: Use Vercel AI SDK core primitives and patterns to design type safe LLM calls, streaming responses, and tool integrations.
- claude.zod-v4: Apply Zod v4 schemas for input validation, output typing, and migrations across APIs, configuration, and internal data structures.

### Usage Guidelines

- Start with `zen.planner` to outline steps based on the research checklist.
- Use `claude.fetch` or `vercel.search_documentation` for external URLs in the checklist (e.g., Vercel Blob docs).
- For local code inspection: Call `next-devtools.nextjs_runtime` on routes like `/api/chat/attachments`.
- Chain tools: e.g., `context7.resolve-library-id` → `context7.get-library-docs` for `@vercel/blob`.
- After coding: Run `zen.codereview` and `zen.secaudit` on changes.
- Invoke tools via standard MCP syntax in your responses (e.g., `exa.deep_search_exa {query: "Vercel Blob Supabase integration examples"}`).

---

## Research checklist

Use MCP tools to fetch and read the following before coding:

1. **Local docs & code**

   - `AGENTS.md`
   - `docs/specs/active/0017-spec-attachments-migration-next.md`
   - `docs/specs/archive/0009-spec-attachments-ssr-listing-and-cache-tags.md`
   - `docs/architecture/decisions/adr-0040-consolidate-supabase-edge-to-vercel-webhooks.md`
   - `docs/architecture/decisions/adr-0041-webhook-notifications-qstash-and-resend.md`
   - `docs/development/env-setup.md`
   - `docs/development/zod-schema-guide.md`
   - `src/app/api/chat/attachments/route.ts`
   - `src/app/api/attachments/files/route.ts`
   - `src/lib/env/server.ts`
   - `src/domain/schemas/env.ts`
   - `src/lib/cache/tags.ts`
   - Any modules dealing with `file_attachments` and trip-related files.

2. **External docs – fetch via `claude.fetch`**

   - Vercel Blob:
     - `https://vercel.com/docs/storage/vercel-blob`
     - `https://vercel.com/docs/storage/vercel-blob/server-upload`
     - `https://vercel.com/docs/vercel-blob/client-upload`
   - Next.js caching and tags:
     - `https://nextjs.org/docs/app/getting-started/caching-and-revalidating`
   - Optional: AI SDK telemetry (for tracing uploads):
     - `https://v6.ai-sdk.dev/docs/ai-sdk-core/telemetry`

3. **Library ID resolution (optional)**

   - Use `context7.resolve-library-id` and `context7.get-library-docs` for:
     - `"@vercel/blob"`
     - `"next/cache"`

---

## Goals

High-level goals:

1. Remove runtime dependency on the legacy backend for attachments.
2. Implement Next.js 16-native attachments routes backed by:
   - Vercel Blob for file bytes.
   - Supabase for metadata.
3. Maintain or improve:
   - Validation (Zod).
   - Performance (using `revalidateTag` and optional cache tags).
   - Security (auth, size limits, MIME types).

Non-goals:

- No complex image transformations (thumbnails, etc.) at this stage.
- No migrations for existing historical attachments beyond what the spec requires
  for v1 (you may outline a path but not implement the full data migration).

---

## Required ADR and SPEC work

### 1. ADR – `docs/architecture/decisions/adr-0058-vercel-blob-attachments.md`

Create or update ADR-0058 with:

- **Context**
  - Describe the current proxy-based architecture.
  - List drawbacks:
    - Hidden dependency on retired backend.
    - Multi-hop network path.
    - Fragmented observability and error handling.
- **Decision**
  - Use **Vercel Blob** for file bytes.
  - Use **Supabase** for metadata and RLS.
  - Chat attachments, trip images, and avatars will follow this pattern over time,
    starting with chat attachments.
- **Consequences**
  - Pros: simple, scalable asset store; unified Next.js-based routing.
  - Cons: requires Blob provision per environment and a migration step.
- **Implementation Notes**
  - Use `put()` from `@vercel/blob` for server uploads:  
    `https://vercel.com/docs/storage/vercel-blob/server-upload`
  - Derive object keys like:
    - `trip/{trip_id}/{uuid-filename}`
    - `user/{user_id}/{uuid-filename}`
  - Enforce size and type limits via Zod.
  - For now, implement **server-side uploads**; leave a clearly documented TODO
    for optional client uploads with `handleUpload` + `upload()`:
    - `https://vercel.com/docs/vercel-blob/client-upload`
- **References**
  - URLs to Vercel Blob docs and Next.js caching docs.

### 2. SPEC – `docs/specs/active/0036-spec-attachments-v2-vercel-blob.md`

Create SPEC-0036 to describe:

- API contracts for:
  - `POST /api/chat/attachments` (upload).
  - `GET /api/attachments/files` (listing).
- Expected request/response payloads.
- Size and type limits.
- Caching and revalidation strategy.
- Security requirements and auth behavior.
- Migration/rollout phases.

Include a `References` section with all relevant URLs.

---

## Implementation tasks

### Step 1 – Environment schema and configuration

1. In `src/domain/schemas/env.ts`:
   - Extend server env schema to include:
     - `BLOB_READ_WRITE_TOKEN` (string, required in production).
     - Optional `BLOB_PUBLIC_BASE_URL` (string or URL) for generating public links.
2. In `src/lib/env/server.ts`:
   - Add helpers:
     - `getBlobReadWriteToken()`.
     - `getBlobPublicBaseUrl()` (if needed).
3. Update:
   - `.env.example` and any env docs in `docs/development/env-setup.md`.

### Step 2 – Upload route (`POST /api/chat/attachments`)

1. Open `src/app/api/chat/attachments/route.ts`.
2. Replace legacy backend proxy logic with:
   - `const formData = await request.formData();`
   - Extract files under the agreed field name (e.g., `files` or `files[]`).
3. Validation:
   - Use Zod v4 for a schema that enforces:
     - Max number of files.
     - Max individual file size.
     - Allowed MIME types.
   - Ensure you follow `docs/development/zod-schema-guide.md`.
4. Upload:
   - For each file:
     - Convert to `BlobPart` (`file.arrayBuffer()` → `Buffer`).
     - Call `put()` from `@vercel/blob`:

       ```ts
       import { put } from '@vercel/blob';

       const blob = await put(path, file.stream(), {
         access: 'public',
         addRandomSuffix: true,
       });
       ```

   - Paths should follow the scheme from SPEC-0036.
5. Metadata:
   - Insert a row into `file_attachments` (or equivalent) with:
     - Owner (user_id).
     - Optional trip_id / chat_message_id.
     - File name, MIME type, size.
     - Blob URL (`blob.url`) and provider (`"vercel_blob"`).
6. Response:
   - Return a JSON payload as described in SPEC-0036, including:
     - Attachment metadata.
     - Direct Blob URLs.
7. Caching:
   - After successful upload, call:
     - `revalidateTag('attachments')` to invalidate attachments listing caches.
   - Optionally, call your Upstash `bumpTag('attachments')` helper.

### Step 3 – Listing route (`GET /api/attachments/files`)

1. Open `src/app/api/attachments/files/route.ts`.
2. Remove legacy backend proxy logic completely.
3. Implement logic:
   - Parse query params:
     - `tripId`, `chatMessageId`, `limit`, `offset`.
   - Use Supabase (SSR client) to:
     - Select from `file_attachments` with filters.
     - Enforce RLS (only records that user is allowed to see).
4. Response:
   - Return items with:
     - `id`, `name`, `size`, `mimeType`, `url`, `createdAt`, `tripId`, etc.
   - Include `nextOffset` or pagination metadata as defined in SPEC-0036.
5. Caching:
   - If listing is safe to cache per user:
     - Use `'use cache'` in a helper function.
     - Mark with `cacheTag('attachments')` so revalidation from upload works.
   - See:
     - `https://nextjs.org/docs/app/getting-started/caching-and-revalidating`

### Step 4 – SPEC-0017 status update

1. In `docs/specs/active/0017-spec-attachments-migration-next.md`:
   - Update the status from “Partial (Proxy Implementation)” to “Implemented”
     (or “Implemented (Phase 1)”).
   - Note that further phases (e.g., client uploads, additional resource types)
     will be tracked in SPEC-0036.

### Step 5 – Testing

1. Unit tests with Vitest:
   - Add tests for:
     - Successful upload of a small file.
     - Rejection of too-large file.
     - Rejection of unsupported MIME type.
   - Reference Vitest docs:
     - `https://vitest.dev/guide/`
2. Integration tests:
   - Optionally, add Playwright/E2E tests for:
     - Uploading a file through UI.
     - Seeing it appear in attachments list.
3. Make sure tests work under CI configuration documented in the repo.

---

## Acceptance criteria

- `POST /api/chat/attachments`:
  - No longer calls `getBackendApiUrl()` or legacy backend endpoints.
  - Uses Vercel Blob `put()` with correct paths and access modes.
  - Inserts Supabase metadata correctly.
  - Enforces Zod-based validation for size/type/count.
- `GET /api/attachments/files`:
  - Returns results from Supabase with correct RLS.
  - Filters and paginates correctly.
  - Can be wired into cache tags if required.
- ADR-0058 and SPEC-0036 exist, are up to date, with references and example payloads.
- SPEC-0017 is updated to reflect current implementation status.
- Tests pass and provide at least basic coverage for upload + listing flows.
