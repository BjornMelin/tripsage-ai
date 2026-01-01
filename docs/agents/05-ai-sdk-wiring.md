# Agent Prompt — AI SDK Wiring

Role: Ensure Vercel AI SDK v6 is wired correctly (models, streaming, tools, error handling, quotas).

## Task Claiming (required)

- Choose a task from `docs/tasks/INDEX.md`, then edit its `docs/tasks/T-###-*.md` file:
  - Set Status to `CLAIMED`
  - Set Owner to your identifier

## Scope

- Route handlers under `src/app/api/**` and AI modules under `src/ai/**`.
- Strictly validate tool inputs (Zod v4 schemas from `@schemas/*`).
- Enforce rate limits for expensive endpoints.

## Verification

- `pnpm biome:fix`
- `pnpm type-check`
- `pnpm test:affected`
- Next DevTools `browser_eval` verification for any UI-exposed AI feature.

## When stuck

- Use `gh_grep.searchGitHub` to find Vercel AI SDK v6 route patterns; record full URLs in the task file.

## References (full URLs)

- [Vercel AI SDK](https://sdk.vercel.ai/docs)
