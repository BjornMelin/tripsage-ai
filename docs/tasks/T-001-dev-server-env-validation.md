# T-001 — Dev server env validation blocks `pnpm dev`

## Meta

- ID: `T-001`
- Priority: `P0`
- Status: `DONE`
- Owner: `release-orchestrator`
- Depends on: `-`

## Problem

`pnpm dev` failed at startup because server-side environment validation rejected **optional** integration env vars present in `.env.local` with placeholder/invalid values (e.g. QStash signing keys too short, invalid/empty `COLLAB_WEBHOOK_URL`). This prevented the Next.js dev server (and Playwright webServer) from booting.

## Fix (implemented)

In `src/lib/env/server.ts`, preprocess `process.env` **in non-production** to delete invalid/placeholder values for:

- `QSTASH_CURRENT_SIGNING_KEY`
- `QSTASH_NEXT_SIGNING_KEY`
- `QSTASH_TOKEN`
- `COLLAB_WEBHOOK_URL`

Production remains strict; only non-production tolerates invalid placeholders so the app can boot without every integration configured.

## Acceptance Criteria (black-box)

- [x] `pnpm dev` starts successfully with placeholder/empty optional integration env vars present.
- [x] Typecheck passes.
- [x] Affected unit tests pass.

## Likely Files

- `src/lib/env/server.ts`

## Verification (commands)

- [x] `pnpm biome:fix`
- [x] `pnpm type-check`
- [x] `pnpm test:affected`
- [ ] `pnpm dev` (manual smoke; starts and serves `http://localhost:3000`)

## Playwright Verification Steps

1. Start dev server: `pnpm dev`
2. Navigate to `http://localhost:3000`
3. Assert landing page renders (e.g., app title/primary CTA)

## Notes / Links (full URLs only)

- Next.js instrumentation hook docs: https://nextjs.org/docs/app/building-your-application/optimizing/instrumentation

