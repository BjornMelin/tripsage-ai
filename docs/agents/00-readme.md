# Parallel Codex Agents — Readme

These prompts are designed to run **multiple independent Codex sessions** against this repo without colliding.

## Non-Negotiables

- **Claim tasks**: edit exactly one file in `docs/tasks/` and set Owner + Status before coding.
- **Browser verification** is mandatory for user-facing changes:
  - Write explicit Next DevTools `browser_eval` steps in the task file (navigate → snapshot → interact → snapshot).
  - If `browser_eval` is unavailable in your environment, run the repo’s Playwright scripts (example: `pnpm test:e2e:chromium`) and document the limitation (fallback: `pnpm exec playwright test --project=chromium`).
- **Shipping > refactoring**: only refactor to unblock shipping or remove defect-causing duplication.
- **Strict typing**: no `any` (TS) and full type hints (Python).
- **Real-world references allowed**: use `gh_grep.searchGitHub` when unsure about patterns/APIs and record full URLs in task notes.

## How to Start a Session

1. Pick an unclaimed task from `docs/tasks/INDEX.md`.
2. Open the task file and set:
   - Status → `CLAIMED`
   - Owner → your session identifier
3. Implement to acceptance criteria.
4. Run the task’s verification commands.
5. Update task Status → `DONE` with evidence.
