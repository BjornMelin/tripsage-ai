# Codex Parallel Session Protocol

This repo is organized for parallel Codex sessions to implement tasks without conflicts.

## Ground Rules

- **Claim work by editing a single task file** in `docs/tasks/` (set Owner + Status).
- Prefer small PR-sized changes per task; avoid drive-by refactors.
- Run verification commands listed in the task before marking it Done.
- Any user-facing change must include Next DevTools `browser_eval` verification steps (or update the existing steps).

## Task Status Values

- `UNCLAIMED`
- `CLAIMED`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

## Merge Conflict Minimization

- One task per file: `docs/tasks/T-###-<slug>.md`
- Avoid editing `docs/tasks/INDEX.md` unless adding/removing tasks; keep it append-only when possible.
- Prefer touching only the files listed in your task’s “Likely files” section.

## Verification Requirements

- JS/TS code changes must pass:
  - `pnpm biome:fix`
  - `pnpm type-check`
  - `pnpm test:affected`
- E2E-impacting changes should run:
  - `pnpm test:e2e:chromium` (or `pnpm exec playwright test --project=chromium`)
  - `pnpm test:e2e` (full browser matrix, when relevant)

## Browser Evidence (Next DevTools `browser_eval`)

- Capture deterministic repro steps in the task file.
- Include screenshots only when needed. If you include links, they must be full URLs (e.g. GitHub permalinks).
