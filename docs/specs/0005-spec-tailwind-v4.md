# Spec: Tailwind CSS v4 Migration

Status: Completed
Last updated: 2025-10-23

## Objective

Finalize migration to Tailwind v4: CSS-first configuration, PostCSS plugin, remove legacy lint integration.

## Implementation Checklist

- [x] Remove `eslint-plugin-tailwindcss` from devDependencies.
- [ ] Add/Confirm `@tailwindcss/postcss` in devDependencies and `postcss.config.*` plugin.
  - [x] Confirmed `@tailwindcss/postcss` present and configured in `frontend/postcss.config.mjs`.
- [x] Run `npx @tailwindcss/upgrade` (forced due to dirty git) and verify globals.css import remains `@import "tailwindcss";`
- [x] Verify utility coverage across `src/app`, `src/components`, and any dynamic class names.
- [x] Document any class rename or behavior changes found during verification.

## Verification results

Date: 2025-10-23

- Replaced one deprecated v3 opacity utility:
  - bg-opacity-75 → bg-black/75 in `frontend/src/components/features/agent-monitoring/dashboard/agent-status-dashboard.tsx`
- Observed outline utilities such as `focus:outline-none` in multiple components. Tailwind v4 introduces `outline-hidden`; current usage remains acceptable and will be revisited if focus styles require adjustment.
- No further v3-only opacity utilities found across representative pages (chat, trips, settings, dashboard).

### Notes from migration run

- @tailwindcss/postcss is configured in `frontend/postcss.config.mjs` and present in devDependencies.
- No root `tailwind.config.{js,ts}` present (v4 CSS-first config). `components.json` still references a default `tailwind.config.js` path for shadcn tooling; safe to leave blank under v4.
- `next dev` script no longer forces `--turbopack` (unused in v16; Turbopack is default).

## References

- Tailwind v4 Upgrade Guide: <https://tailwindcss.com/docs/upgrade-guide>
