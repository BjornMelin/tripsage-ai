# Local Supabase + RAG E2E (Reproducible Dev Setup)

Step-by-step instructions to run TripSage locally with a **real Supabase local database**, seeded data, and a quick end-to-end RAG verification.

For general onboarding, start with `docs/development/core/quick-start.md`.

## Prerequisites

- Node.js ≥24 and pnpm ≥9
- Docker-compatible container runtime (required for `pnpm supabase:*`)

## 1) Install deps

```bash
pnpm install
```

## 2) Create env files

```bash
cp .env.local.example .env.local
cp .env.test.example .env.test
```

## 3) Start Supabase local + seed data

```bash
pnpm supabase:bootstrap
pnpm supabase:status
pnpm supabase:reset:dev
```

Then copy values from `pnpm supabase:status` into `.env.local`:

- `NEXT_PUBLIC_SUPABASE_URL` → “Project URL”
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (preferred) **or** `NEXT_PUBLIC_SUPABASE_ANON_KEY` (legacy)
- `SUPABASE_SERVICE_ROLE_KEY` → use the `sb_secret_...` value (server-only)
- `SUPABASE_JWT_SECRET` → use the `JWT_SECRET` value (recommended; required for some non-test security flows)

Notes:

- Seed output prints login credentials (example: `dev.owner@example.local` / `dev-password-change-me`).
- Local confirmation inbox is at `http://localhost:54324` (sometimes labeled “Mailpit” in `pnpm supabase:status`).

## 4) Run the app

```bash
pnpm dev
```

Sign in using a seeded user (printed by `pnpm supabase:reset:dev`), then navigate to `/dashboard`.

## 5) RAG smoke test (real DB)

This validates: seeded `rag_documents` exist → retrieval via `hybrid_rag_search` works → the agent tool wiring (`ragSearch`) works.

1) Go to `/chat`.
2) Ask:
   - `Use the ragSearch tool to search my user_content documents for "deterministic seed attachment" and summarize what you find.`

Expected:

- The assistant executes a `ragSearch` tool call.
- Results include snippets from seeded `user_content` attachments (e.g. `hello.txt`, `sample.pdf`, `sample.docx`, `sample.csv`).

### Embeddings & reranking keys (optional)

- If `AI_GATEWAY_API_KEY` **or** `OPENAI_API_KEY` is set, embeddings are real (`openai/text-embedding-3-small`, 1536-d).
- If no embedding provider key is set, the app uses a deterministic 1536-d fallback (non-semantic; do not use it to judge relevance).
- If `TOGETHER_AI_API_KEY` is set, reranking is enabled; otherwise it’s a no-op reranker.

## 6) Verify / build / test

```bash
pnpm biome:check
pnpm type-check
pnpm test
pnpm build
```

## 7) Playwright E2E (automation)

Playwright is runnable without Supabase local. By default, it uses a mock Supabase Auth HTTP server started by `scripts/e2e-webserver.mjs` (the tests are not intended to validate DB/RLS/RAG end-to-end).

```bash
pnpm exec playwright install chromium
pnpm test:e2e:chromium
```

If you need **DB-backed** end-to-end validation (RLS/RAG/attachments), use the “RAG smoke test (real DB)” above and manual QA flows against Supabase local.

## 8) Type generation (when migrations change)

After changing `supabase/migrations/20260120000000_base_schema.sql`:

```bash
pnpm supabase:db:reset
pnpm supabase:typegen
```

This updates `src/lib/supabase/database.types.ts` from the local database schemas.

## Troubleshooting

- If `pnpm dev` starts on a different port, use the printed URL (e.g. `http://localhost:3001`).
- Prefer repo scripts (`pnpm supabase:*`) over running `supabase ...` directly; the scripts encode local stack workarounds and keep behavior reproducible.
