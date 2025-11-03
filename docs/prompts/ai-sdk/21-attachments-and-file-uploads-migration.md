# Prompt: Attachments & File Uploads Migration (Next.js + Supabase Storage)

## Executive summary

- Goal: Migrate Python/FastAPI attachments endpoints to Next.js Route Handlers with Supabase Storage, signed URLs, MIME/size validation, and stricter rate limits.
- Outcome: A secure, SSR-only storage flow with upload and retrieval via signed URLs, unified observability, and FastAPI attachments router deleted.

## Custom persona

- You are “AI SDK Migrator (Attachments)”. You deliver a minimal, secure, storage flow.
  - Library-first, final-only; keep to KISS/DRY/YAGNI.
  - Autonomously use: zen.planner, zen.thinkdeep, zen.analyze, zen.consensus (≥9.0/10), zen.secaudit, zen.challenge, zen.codereview; exa.web_search_exa, exa.crawling_exa, exa.get_code_context_exa; firecrawl_scrape.
  - Success criteria: Next handlers provide upload + signed URL retrieval with validation + RL; tests pass; Python attachments router removed.

## Docs & references (research first)

- Supabase SSR (Next.js): <https://supabase.com/docs/guides/auth/server-side/nextjs>
- Supabase Storage (buckets, signed URLs): <https://supabase.com/docs/guides/storage>
- Next.js App Router: <https://v6.ai-sdk.dev/docs/getting-started/nextjs-app-router>
- Upstash RL template: <https://vercel.com/templates/next.js/ratelimit-with-upstash-redis>
- Vercel OTel & Drains: <https://vercel.com/docs/otel> , <https://vercel.com/docs/drains/reference/traces>

## Tools to use (explicit)

- exa.web_search_exa: Next.js + Supabase Storage signed URLs, best practices
- exa.crawling_exa: Supabase Storage signed URL docs; SSR client integration
- firecrawl_scrape: Single page excerpts for code patterns
- exa.get_code_context_exa: Example handlers for multipart uploads + signed URLs
- zen.planner: steps; one in_progress
- zen.consensus: decide storage validation and flows (≥9.0/10)
- zen.secaudit: ensure SSR-only keys; no PII leaks
- zen.codereview: finalize doc

## Plan (overview)

1) Storage Design
   - Choose bucket structure and retention; define allowed MIME types and size limits.
   - Define metadata stored in DB (filename, mime, size, owner_id, created_at; optional trip_id).
2) Route Handlers
   - POST /api/attachments/upload: accept multipart/form-data; validate MIME/size; upload to bucket server-side (SSR); return minimal metadata.
   - GET /api/attachments/signed-url?id=...: validate ownership; return signed URL with short TTL.
3) Rate Limiting
   - Apply stricter limits for uploads via shared Upstash helper; identify by user.id.
4) Observability & Security
   - Add OTel spans (svc.storage.upload, svc.storage.signedurl); redact logs; SSR-only secrets.
5) Tests & Decommission
   - Vitest: upload success/failure; signed URL behavior; ownership checks; RL 429.
   - Remove tripsage/api/routers/attachments.py and related Python code.

## Checklist (mark off; add notes under each)

- [ ] Define bucket + metadata schema
- [ ] Write upload + signed-url handler plans (SSR-only; no client secrets)
- [ ] Integrate RL via shared module
- [ ] Observability spans + redaction notes
- [ ] Vitest tests defined
- [ ] Delete Python attachments router + references

## Working instructions (mandatory)

- Never expose storage service keys to client; SSR-only.
- Validate file MIME and size; consider optional scanning if policy requires (documented, not implemented here).
- Keep responses minimal; avoid storing PII in metadata without RLS.

## Process flow (required)

1) Research (exa/firecrawl) → 2) Plan (zen.planner) → 3) Decide (zen.consensus ≥9.0) → 4) Security (zen.secaudit) → 5) Review (zen.codereview)

## File & module targets

- frontend/src/app/api/attachments/upload/route.ts
- frontend/src/app/api/attachments/signed-url/route.ts
- frontend/src/lib/storage/index.ts
- frontend/tests/attachments/*.test.ts

## Legacy mapping (delete later)

- Delete: tripsage/api/routers/attachments.py and any attachments helpers in Python.

## Testing requirements

- Upload happy path and invalid MIME/oversize
- Ownership checks on signed URL issuance
- RL 429 with Retry-After; OTel spans present; no PII in logs
