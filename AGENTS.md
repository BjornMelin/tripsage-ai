# Repository Guidelines

## ExecPlans

When writing complex features or significant refactors, use an ExecPlan (as described in [.agent/PLANS.md](.agent/PLANS.md)) from design to implementation.

## Project Structure & Module Organization

For detailed project structure information, see [docs/architecture/project-structure.md](../docs/architecture/project-structure.md).

**Key Guidelines:**

- `tripsage/api/` hosts the FastAPI application entry point and core API logic.
- `tripsage_core/` holds domain services, models, and shared exceptions—extend
  logic here, not in API layers. Services are split into `business/` and `infrastructure/` subdirectories.
- `frontend/src/` is the Next.js 16 workspace with `app/`, `components/`, `lib/`, `hooks/`, `contexts/`, `stores/`, `types/`, and `schemas/` directories.
- `tests/` splits into `unit/`, `integration/`, `e2e/`, `performance/`, and `security/`; fixtures live in `tests/fixtures/` and `tests/factories/`.
- Supporting automation sits in `scripts/` and `docker/`; configuration samples ship with `.env.example`.

## Build, Test, and Development Commands

- Bootstrap: `uv sync` for Python deps, `cd frontend && pnpm install` for web
  deps.
- Run services: `uv run python -m tripsage.api.main` (API, port 8000) and
  `cd frontend && pnpm dev` (Next.js, port 3000).
- Quality gates: `ruff format . && ruff check . --fix`, `uv run pyright`,
  `uv run pylint tripsage tripsage_core`.
- Testing: `uv run pytest --cov=tripsage --cov=tripsage_core`
  (fails under 90% coverage) plus `pnpm test` and `pnpm test:e2e` for Vitest and
  Playwright.
- Containers: `docker-compose up --build` spins the stack with Supabase
  services.

## Frontend Agent Instructions (MANDATORY)

- When working on any files under `frontend/` (including `@frontend/*` paths or imports aliased to `@/` inside the frontend workspace), you MUST read and follow `frontend/AGENTS.md`.
- The instructions in `frontend/AGENTS.md` are the single source of truth for the frontend stack (Next.js 16, React 19, AI SDK v6, Supabase SSR, Upstash, Tailwind v4, Biome, Vitest). They supersede and take precedence over root‑level guidance wherever there is overlap within the `frontend/` directory tree.
- Always load and reference `frontend/AGENTS.md` before making changes in `frontend/`. Start here:
  - Frontend Guide: `frontend/AGENTS.md`
  - Entry points and examples referenced inside the guide include: `frontend/src/app/chat/page.tsx`, `frontend/src/app/api/**/route.ts`, `frontend/src/lib/providers/registry.ts`, `frontend/middleware.ts`.

## Coding Style & Naming Conventions

- Python: type hints everywhere, Google-style docstrings, 88-char lines per
  `pyproject.toml`, async-first service calls; exceptions derive from
  `CoreTripSageError`.
- TypeScript: strict mode, hooks/components as PascalCase in `frontend/app`,
  utilities as camelCase modules in `frontend/lib`.
- Formatting is automated via Ruff and Biome; never hand-format generated
  OpenAPI clients—regenerate instead.

## Testing Guidelines

- Name backend tests `test_*.py`; group them under the matching package path,
  for example `tests/unit/api/test_trips.py`.
- Keep fixtures declarative in `tests/fixtures/` and prefer factory helpers
  over hard coded JSON.
- Aim for ≥90% backend coverage (CI enforced) and ≥85% frontend coverage (run
  `pnpm test:coverage`); document risk waivers in PRs if thresholds dip.

## Commit & Pull Request Guidelines

- Use Conventional Commit messages (`feat:`, `fix:`, `chore:`) aligning with the
  current history and Keep a Changelog sections.
- PRs must describe scope, list validation commands, and link Linear or Jira IDs;
  attach screenshots for UI impacting changes.
- Rebase before opening PR, ensure lint, type, and test gates pass, and
  request reviewers with domain ownership.

## Security & Configuration Tips

- Never commit secrets; copy from `.env.example` and store overrides in your
  `.env`.
- Verify platform connectivity with
  `uv run python scripts/verification/verify_connection.py` and related checks
  before pushing.
- Enable Husky hooks (`pnpm prepare`) locally so lint-staged blocks unsafe
  commits.
