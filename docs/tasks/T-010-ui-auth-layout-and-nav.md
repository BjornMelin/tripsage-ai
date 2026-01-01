# T-010 — UI Audit + Auth Layout Fix + Remove Duplicate Navbar

## Meta

- ID: `T-010`
- Priority: `P0`
- Status: `DONE`
- Owner: `codex-session-t010-a`
- Depends on: `-`

## Problem

- Landing page shows duplicate primary navigation / header.
- Auth pages (`/login`, `/register`, `/reset-password`) have broken/squished layout at common breakpoints.

## Issues Found (Phase B)

1. **Duplicate navbar on `/`**
   - Evidence: `/tmp/playwright-mcp-output/1767245162148/page-2026-01-01T05-26-11-850Z.png` (two `banner` landmarks).
   - Root cause: `src/app/(marketing)/layout.tsx` renders `Navbar`, and `src/app/(marketing)/page.tsx` also rendered its own `<header>`.

2. **Auth layout “squishes” `/login` + `/register` and duplicates chrome**
   - Evidence: `/tmp/playwright-mcp-output/1767245162148/page-2026-01-01T05-26-26-200Z.png` and `/tmp/playwright-mcp-output/1767245162148/page-2026-01-01T05-26-50-612Z.png` (extra `banner` + `contentinfo` from `AuthLayout`).
   - Root cause: `src/app/(auth)/layout.tsx` wrapped pages in `AuthLayout` (`max-w-md` container + header/footer) even though pages already provide full-screen layouts.

3. **Duplicate help links on `/reset-password`**
   - Evidence: `/tmp/playwright-mcp-output/1767245162148/page-2026-01-01T05-40-05-596Z.png` (duplicate “Back to sign in” / “Contact support” blocks).
   - Root cause: `ResetPasswordForm` already includes these links; the page added another block.

## Fixes Implemented (T-010 scope)

- Remove duplicate landing header; keep a single navbar.
- Remove auth wrapper that constrained/squished auth pages; keep semantic `main` landmark without adding extra chrome.
- Remove duplicate reset-password help block.
- Support both `from` and `next` query params on `/login` + `/register` so redirects preserve intended return paths (matches existing redirect patterns in the app).
- Make marketing navbar sticky (and match fallback) for consistent behavior.

## Acceptance Criteria (black-box)

- [x] Landing page (`/`) shows exactly one primary navbar/header (no duplicate nav regions, no duplicate “TripSage AI” header stacks).
- [x] Login (`/login`) and Register (`/register`) are centered and readable on mobile + desktop.
- [x] Auth pages do not overflow horizontally; primary headings/CTAs are not clipped.
- [x] Fixes are verified via Next DevTools `browser_eval` snapshots (before/after).
- [x] Quality gates pass: `pnpm biome:fix`, `pnpm type-check`, `pnpm test:affected`.

## Likely Files

- `src/app/(marketing)/layout.tsx`
- `src/app/(marketing)/page.tsx`
- `src/components/layouts/navbar.tsx`
- `src/app/(auth)/layout.tsx`
- `src/app/(auth)/login/page.tsx`
- `src/app/(auth)/register/page.tsx`
- `src/app/(auth)/reset-password/page.tsx`
- `src/components/auth/*`

## Evidence (runtime + browser snapshots)

### Before

- `/` — `/tmp/playwright-mcp-output/1767245162148/page-2026-01-01T05-26-11-850Z.png`
- `/login` — `/tmp/playwright-mcp-output/1767245162148/page-2026-01-01T05-26-26-200Z.png`
- `/register` — `/tmp/playwright-mcp-output/1767245162148/page-2026-01-01T05-26-50-612Z.png`
- `/reset-password` — `/tmp/playwright-mcp-output/1767245162148/page-2026-01-01T05-26-57-615Z.png`

### After

- `/` — `/tmp/playwright-mcp-output/1767245162148/page-2026-01-01T05-39-06-440Z.png`
- `/login` — `/tmp/playwright-mcp-output/1767245162148/page-2026-01-01T05-39-23-084Z.png`
- `/register` — `/tmp/playwright-mcp-output/1767245162148/page-2026-01-01T05-39-33-558Z.png`
- `/reset-password` — `/tmp/playwright-mcp-output/1767245162148/page-2026-01-01T05-40-38-493Z.png`

## Files Changed

- `src/app/(marketing)/layout.tsx` — Navbar fallback matches sticky navbar behavior.
- `src/app/(marketing)/page.tsx` — Remove duplicate landing header.
- `src/components/layouts/navbar.tsx` — Sticky navbar (public marketing only).
- `src/app/(auth)/layout.tsx` — Remove `AuthLayout` wrapper; provide semantic `main` landmark.
- `src/app/(auth)/login/page.tsx` — Accept `next` as an alias for `from` when computing post-login redirect.
- `src/app/(auth)/register/page.tsx` — Accept `next` as an alias for `from` when computing post-signup redirect.
- `src/app/(auth)/reset-password/page.tsx` — Remove duplicate help block.
- `src/components/layouts/auth-layout.tsx` — Deleted (unused after layout fix).
- `docs/development/core/troubleshooting.md` — Fix Vitest watch-mode command reference (`pnpm exec vitest`).
- `docs/development/testing/testing.md` — Clarify test command behavior and watch-mode usage.
- `AGENTS.md` — Clarify `pnpm test` (single-run) vs `pnpm exec vitest` (watch mode).

## Verification (commands)

- `pnpm biome:fix`
- `pnpm type-check`
- `pnpm test:affected`

Outputs:
- `pnpm biome:fix` → “No fixes applied.”
- `pnpm type-check` → pass (exit 0).
- `pnpm test:affected` → pass (exit 0, no affected tests).

## Playwright Verification Steps (next-devtools `browser_eval`)

1. Start browser automation (`browser=chrome`).
2. Navigate + snapshot:
   - `http://localhost:<port>/`
   - `http://localhost:<port>/login`
   - `http://localhost:<port>/register`
   - `http://localhost:<port>/reset-password`
3. Assert:
   - Exactly one primary navigation region/header on `/`.
   - Auth pages have a single `main` landmark with centered content and no horizontal overflow.
   - No console errors during render.

Runtime validation:
- `next-devtools.nextjs_call:get_errors` → “No errors detected in 2 browser session(s).”
- Public dashboard check: navigating to `/dashboard` redirects to `/login?next=%2Fdashboard` (no public dashboard access without auth).

## Notes / Links (full URLs only)

### shadcn/ui

- `https://ui.shadcn.com/docs/components/sheet` (reviewed via shadcn registry + `sheet-demo` example).
- `https://ui.shadcn.com/docs/components/navigation-menu` (reviewed via shadcn registry + `navigation-menu-demo` example).

### Supabase Auth (SSR + UX)

- `https://supabase.com/docs/guides/auth/server-side`
- `https://supabase.com/docs/guides/auth/quickstarts/nextjs`
- `https://supabase.com/docs/guides/auth/redirect-urls`
- `https://supabase.com/docs/guides/auth/passwords`
- `https://supabase.com/docs/reference/javascript/auth-resetpasswordforemail`
- `https://supabase.com/docs/guides/auth/auth-email-templates`
