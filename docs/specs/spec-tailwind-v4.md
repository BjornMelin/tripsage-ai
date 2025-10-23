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
- [ ] Run `npx @tailwindcss/upgrade` and commit generated CSS config files.
- [ ] Verify utility coverage across `src/app`, `src/components`, and any dynamic class names.
- [ ] Document any class rename or behavior changes found during verification.

## References

- Tailwind v4 Upgrade Guide: <https://tailwindcss.com/docs/upgrade-guide>
