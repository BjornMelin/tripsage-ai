# ADR-0016: Tailwind CSS v4 migration (CSS-first configuration)

**Date**: 2025-10-23

## Status

Accepted

## Context

Tailwind v4 adopts CSS-first configuration and deprecates some v3-era plugin/ESLint integrations.

## Decision

- Install and use `@tailwindcss/postcss`.
- Remove legacy ESLint Tailwind plugin dependency.
- Plan to run `npx @tailwindcss/upgrade` and review CSS config.

## Consequences

### Positive

- Faster, simpler config; less JS glue.

### Negative

- Possible manual CSS adjustments in complex projects.

### Neutral

- Linting enforcement may move from an ESLint plugin to CSS-level or styleguide checks; no functional impact expected.

## Alternatives Considered

### Alternative 1 — Remain on Tailwind v3

Rejected due to performance and maintenance drawbacks; v4 provides significant improvements and simplified configuration.

### Alternative 2 — Replace Tailwind with custom CSS/PostCSS

Rejected; higher implementation cost and loss of utility workflow ergonomics used across the codebase.

## References

- Tailwind v4 upgrade guide and announcement.
  - <https://tailwindcss.com/docs/upgrade-guide>
  - <https://tailwindcss.com/blog/tailwindcss-v4>
