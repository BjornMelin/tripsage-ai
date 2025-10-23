# CI Overview

TripSage uses a minimal GitHub Actions setup for quality and security:

- `CI` (`.github/workflows/ci.yml`): runs on PRs and pushes. Two jobs:
  - Backend: ruff lint, pyright (temporarily soft-fail), unit tests (temporarily soft-fail).
  - Frontend: Biome lint, TypeScript `--noEmit`, unit tests.
  - Path filters ensure each job runs only for relevant changes.
  - No matrices, no comment bots, and no redundant quality gates.

- `Weekly Security` (`.github/workflows/security.yml`): runs weekly and on-demand.
  - Gitleaks scan with redaction. Prefer GitHub Advanced Secret Scanning when available.
  - Example env templates are excluded in `.github/secret_scanning.yml` to prevent false positives.

## Transition plan

Type checks and backend unit tests are temporarily marked `continue-on-error` while the codebase stabilizes. After three consecutive green runs on `main`, we will convert them to blocking.

## Branch protections

Configure required checks to use the `CI` workflow jobs (Backend, Frontend). Remove any references to legacy workflow names.

## Adding new checks

When adding new checks, prefer inlining steps in `ci.yml` to avoid bespoke composite actions. Keep jobs small, fast, and path-scoped.

## Paths monitored

To avoid missing critical validation when only tests or dependency definitions change, CI triggers when any of the following change:

- Backend code and configs: `tripsage/**`, `tripsage_core/**`, `scripts/**`, `supabase/**`, `pyproject.toml`, `ruff.toml`, `pyrightconfig.json`, `setup.cfg`, `pytest.ini`
- Backend tests and lockfile: `tests/**`, `uv.lock`
- Frontend: `frontend/**`
- CI config: `.github/workflows/**`
