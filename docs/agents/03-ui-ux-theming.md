# Agent Prompt — UI/UX & Theming

Role: Finish unwired UI, accessibility, and critical UX polish needed for v1.

## Task Claiming (required)

- Choose a task from `docs/tasks/INDEX.md`, then edit its `docs/tasks/T-###-*.md` file:
  - Set Status to `CLAIMED`
  - Set Owner to your identifier

## Scope

- UI components, navigation, forms, error states, empty states.
- Prefer existing UI primitives (Radix + Tailwind + shadcn registries).
- Avoid new design systems or heavy abstractions.

## Verification

- `pnpm biome:fix`
- `pnpm type-check`
- `pnpm test:affected`
- Next DevTools `browser_eval` verification steps for main UX paths.

## When stuck

- Use `gh_grep.searchGitHub` for real-world accessibility/test selector patterns; record full URLs in the task file.

## References (full URLs)

- shadcn/ui: https://ui.shadcn.com
- Radix UI: https://www.radix-ui.com/primitives
- Tailwind CSS: https://tailwindcss.com
