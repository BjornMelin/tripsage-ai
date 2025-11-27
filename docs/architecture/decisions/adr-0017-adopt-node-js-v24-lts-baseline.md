# ADR-0017: Adopt Node.js v24 LTS baseline

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-10-23
**Category**: platform
**Domain**: Node.js 24

## Context

Our frontend stack targets modern Node features and Next.js 16. Standardizing on Node 24 LTS improves consistency locally and in CI.

## Decision

- Set `engines.node` >=24 in package.json and add `.nvmrc`/`.node-version` to pin.

## Consequences

### Positive

- Consistent developer and CI runtime; aligns with Next.js 16 docs.

### Negative

- Requires contributors to upgrade local Node.

### Neutral

- Toolchain remains unchanged (pnpm, Next, Vitest); only the runtime baseline is lifted.

## Changelog

- 1.0.0 (2025-10-24) — Standardized metadata and formatting; added version and changelog.

## Alternatives Considered

### Alternative 1 — Keep Node 22 LTS

Rejected: Next 16 benefits from newer Node features; alignment across environments is simplified with a single latest LTS.

### Alternative 2 — Avoid engines and rely on local nvm/Volta only

Rejected: engines field offers CI/automation parity and clear feedback for mismatched versions.

## References

- Node.js releases and LTS schedule
  - <https://nodejs.org/en/about/previous-releases>
- Next.js 16 runtime guidance
  - <https://nextjs.org/docs/app/guides/upgrading/version-16#nodejs-runtime-and-browser-support>
