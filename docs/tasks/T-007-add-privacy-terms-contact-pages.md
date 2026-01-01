# T-007 — Add `/privacy`, `/terms`, `/contact` pages (and fix broken legal links)

## Meta

- ID: `T-007`
- Priority: `P0`
- Status: `DONE`
- Owner: `release-orchestrator`
- Depends on: `-`

## Problem

The marketing footer and the registration form link to `/privacy`, `/terms`, and `/contact`, but these routes do not exist and return 404.

Evidence:

- Landing footer links (browser snapshot via Next DevTools `browser_eval`): `http://localhost:3000/privacy`, `http://localhost:3000/terms`, `http://localhost:3000/contact` → all 404.
- Registration form includes explicit legal agreement links to `/terms` and `/privacy` (see `src/components/auth/register-form.tsx`).
- Route inventory does not contain `/privacy`, `/terms`, or `/contact` (see `docs/release/_logs/nextjs-routes.json`).

## Acceptance Criteria (black-box)

- [ ] `http://localhost:3000/privacy` renders a public page (not a 404).
- [ ] `http://localhost:3000/terms` renders a public page (not a 404).
- [ ] `http://localhost:3000/contact` renders a public page (not a 404).
- [ ] The marketing footer links and register form legal agreement links successfully navigate to the above pages.
- [ ] Pages include basic SEO metadata (title + description) via `export const metadata` (static) or `generateMetadata` (if needed).

## Likely Files

- `src/app/(marketing)/page.tsx` (footer link source)
- `src/components/auth/register-form.tsx` (links under checkbox)
- New files expected:
  - `src/app/(marketing)/privacy/page.tsx` (or `src/app/privacy/page.tsx` depending on routing strategy)
  - `src/app/(marketing)/terms/page.tsx`
  - `src/app/(marketing)/contact/page.tsx`
  - Optional: shared content components in `src/components/marketing/*`

## Verification (commands)

- `pnpm biome:fix`
- `pnpm type-check`
- `pnpm test:affected`

## Playwright Verification Steps (next-devtools `browser_eval`)

1. Navigate to `http://localhost:3000/`.
2. Snapshot the page; click footer “Privacy”, assert URL is `/privacy` and page renders a heading.
3. Back; click footer “Terms”, assert URL is `/terms` and page renders a heading.
4. Back; click footer “Contact”, assert URL is `/contact` and page renders a heading.
5. Navigate to `http://localhost:3000/register`.
6. Click “Terms of Service” and “Privacy Policy” links in the legal agreement line; assert both land on non-404 pages.

## Notes / Links (full URLs only)

- Next.js routing: https://nextjs.org/docs/app/getting-started/layouts-and-pages
- Next.js metadata (static `export const metadata` and `generateMetadata`): https://nextjs.org/docs/app/api-reference/functions/generate-metadata
- Next.js not-found conventions (for comparison / guardrails): https://nextjs.org/docs/app/api-reference/file-conventions/not-found
