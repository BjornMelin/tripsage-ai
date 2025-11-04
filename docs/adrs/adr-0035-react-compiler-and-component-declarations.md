# ADR-0035: Enable React Compiler and enforce named component declarations

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-04
**Category**: frontend
**Domain**: Next.js / React 19
**Related ADRs**: ADR-0015, ADR-0023, ADR-0031
**Related Specs**: SPEC-0002, SPEC-0005, SPEC-0016

## Context

The codebase is on React 19 and Next.js 16. We previously migrated to App Router and Tailwind v4, and adopted AI SDK v6 on the frontend. To improve runtime performance and reduce ad-hoc memoization, we want to enable the React Compiler. In parallel, we want consistent component declarations (top-level, named, PascalCase) to improve stack traces, compiler effectiveness, and alignment with React 19 and the React Compiler recommendations.

## Decision

- Enable the React Compiler at the Next.js level via `reactCompiler: true` in `next.config.ts`.
- Enforce top-level named component declarations and proper `forwardRef` usage (named inner function), no anonymous defaults.
- Avoid wrapper abstractions unless they cut ≥2× work; prefer direct imports from libraries.

## Consequences

### Positive

- Fewer manual `useMemo`/`useCallback` cases; compiler optimizes render paths automatically.
- More stable component identities and better DevTools traces via named declarations.
- Aligns with Next.js 16 best practices; keeps performance wins mostly configuration-only.

### Negative

- Initial build may surface compiler warnings requiring local refactors (purity/closures).
- Small risk of edge-case regressions in rarely used components; requires build validation.

### Neutral

- Does not change routing structure or CSS pipeline.

## Alternatives Considered

### Keep compiler disabled

- Lower risk immediately, but misses easy performance wins and requires more manual memoization. Rejected.

### Partial/annotation-only adoption

- Could limit scope, but increases maintenance by managing annotations. We prefer full enablement and fix issues as they arise.

## References

- Next.js 16 `reactCompiler` docs: <https://nextjs.org/docs/app/api-reference/config/next-config-js/reactCompiler>
- React Compiler overview: <https://react.dev/learn/react-compiler/introduction>
