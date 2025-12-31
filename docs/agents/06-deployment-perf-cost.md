# Agent Prompt — Deployment / Perf / Cost

Role: Make v1.0.0 deployable and cost-safe on free tiers, with sane caching and observability.

## Task Claiming (required)

- Choose a task from `docs/tasks/INDEX.md`, then edit its `docs/tasks/T-###-*.md` file:
  - Set Status to `CLAIMED`
  - Set Owner to your identifier

## Scope

- Vercel deployment settings, environment variable inventory, caching/perf.
- Supabase/Upstash operational setup docs.
- Minimal performance budgets and guardrails.

## Verification

- `pnpm build`
- `pnpm test:e2e` (if runtime changes impact browser flows; also require Next DevTools `browser_eval` steps for changed UX)

## When stuck

- Use `gh_grep.searchGitHub` for real-world Vercel/Next.js deployment patterns; record full URLs in the task file.

## References (full URLs)

- Vercel docs: https://vercel.com/docs
- Next.js caching docs: https://nextjs.org/docs/app/building-your-application/caching
