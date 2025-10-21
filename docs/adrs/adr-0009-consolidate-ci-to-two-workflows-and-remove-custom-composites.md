# ADR-0009: Consolidate CI to two workflows and remove custom composites

**Date**: 2025-10-18

## Status

Proposed

## Context

Our repository accumulated multiple GitHub Actions workflows (backend-ci, frontend-ci, security-ci, utilities, example-composite-actions) and three custom composite actions (setup-python, setup-node, security-scan). These introduce duplication (checkout/setup/caching repeated), overlapping gates (redundant quality gates and comment bots), and brittle implementations (ad‑hoc grep-based secret scanning). Pipelines are slow, noisy, and often red-by-default due to strict gates on a codebase that currently fails type checks and tests.

This violates our KISS/DRY/YAGNI principles and increases maintenance cost. We need a minimal, durable CI topology that provides fast, trusted signal while we stabilize the codebase.

## Decision

We will consolidate CI into exactly two workflows and remove bespoke composites:

1) ci.yml (single PR/push workflow): two small jobs (backend, frontend) gated by path filters; use official actions (setup‑python, setup‑node) and minimal steps (lint, type, unit).

2) security.yml (weekly + manual): a focused secrets scan using GH Advanced Secret Scanning configuration or gitleaks. Example env files will be excluded via `.github/secret_scanning.yml` to prevent false positives.

We will delete legacy workflows (backend-ci, frontend-ci, security-ci, utilities, example-composite-actions) and composite actions (setup-python, setup-node, security-scan). Type checks and unit tests will be soft-fail initially (continue-on-error) and flipped to blocking after sustained stability on `main`.

## Consequences

### Positive

- 60–80% fewer CI jobs per PR; quicker signal and lower cost.
- One canonical status surface; reduced reviewer noise (no comment bots/quality-gates).
- No bespoke composites to maintain; rely on supported actions.
- Secret scanning configured declaratively (paths-ignore) instead of brittle grep.

### Negative

- Short migration window: remove legacy workflows and update branch protections.
- Temporary soft-fail gates mean CI may be green while known issues are tracked in summaries.

### Neutral

- Label/reviewer automations are not strictly required; can be reintroduced minimally under ci.yml if a future need is documented.

## Alternatives Considered

### Split workflows per domain and keep utilities

Retain backend/front-end workflows and composite actions for reuse. Rejected: preserves fragmentation, higher upkeep, and continued noise.

### Single ci.yml but keep utilities for labels/comments

Partial simplification with some utility steps. Rejected: still adds maintenance and comment noise without hard requirements.

## References

- GitHub Docs: secret_scanning.yml paths-ignore (UNVERIFIED)
- Internal CI analysis and security scanning review (this PR)
