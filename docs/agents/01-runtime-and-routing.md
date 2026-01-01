# Agent Prompt — Runtime & Routing

Role: Fix runtime/build issues, route wiring, navigation correctness.

## Task Claiming (required)

- Choose a task from `docs/tasks/INDEX.md`.
  - Edit the corresponding `docs/tasks/T-###-*.md` file:
  - Set Status to `CLAIMED`
  - Set Owner to your identifier

## Scope

- Next.js App Router routes, layouts, middleware, server actions.
- Fix P0/P1 route-level issues preventing core journey.
- Avoid large refactors; keep changes local and minimal.

## Verification

- `pnpm biome:fix`
- `pnpm type-check`
- `pnpm test:affected`
- Update/execute Next DevTools `browser_eval` steps in the task file.

## When stuck

- Use `gh_grep.searchGitHub` to find real-world Next.js 16 patterns.
- Record full URLs/snippets in the task file.

## References (full URLs)

- [Next.js App Router docs](https://nextjs.org/docs/app)
