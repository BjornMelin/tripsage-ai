# Spec: Tailwind CSS v4 Migration

Owner: UI/Design Systems
Status: In progress
Last updated: 2025-10-23

## Objective

Finalize migration to Tailwind v4: CSS-first configuration, PostCSS plugin, remove legacy lint integration.

## Implementation Checklist

- [x] Remove `eslint-plugin-tailwindcss` from devDependencies.
- [ ] Add/Confirm `@tailwindcss/postcss` in devDependencies and `postcss.config.*` plugin.
  - [x] Confirmed `@tailwindcss/postcss` present and configured in `frontend/postcss.config.mjs`.
- [x] Run `npx @tailwindcss/upgrade` (forced due to dirty git) and verify globals.css import remains `@import "tailwindcss";`
- [ ] Verify utility coverage across `src/app`, `src/components`, and any dynamic class names.
- [ ] Document any class rename or behavior changes found during verification.

### Notes from migration run

- @tailwindcss/postcss is configured in `frontend/postcss.config.mjs` and present in devDependencies.
- No root `tailwind.config.{js,ts}` present (v4 CSS-first config). `components.json` still references a default `tailwind.config.js` path for shadcn tooling; safe to leave blank under v4.
- `next dev` script no longer forces `--turbopack` (unused in v16; Turbopack is default).

## References

- Tailwind v4 Upgrade Guide: <https://tailwindcss.com/docs/upgrade-guide>
