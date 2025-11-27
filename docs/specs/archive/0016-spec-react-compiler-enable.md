# SPEC-0016: Enable React Compiler in Next.js 16

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-04
**Category**: frontend
**Domain**: Next.js / React 19
**Related ADRs**: [ADR-0035](../../architecture/decisions/adr-0035-react-compiler-and-component-declarations.md)
**Related Specs**: [SPEC-0002](0002-spec-next16-migration.md), [SPEC-0005](0005-spec-tailwind-v4.md)

## Overview

Enable the React Compiler for Tripsage frontend to improve render performance and reduce manual memoization. Keep changes minimal and configuration-first.

## Configuration

- Set `reactCompiler: true` in `frontend/next.config.ts`.
- Keep existing `compiler.removeConsole` and other settings unchanged.

## Scope

- This change does not alter routing, data fetching, or Tailwind setup.
- Address any compiler warnings by local, narrow refactors if surfaced during build.

## Testing

- Run `pnpm build` and ensure no compiler-related errors.
- Run full type-check and tests after enabling to detect regressions.

## Risks & Mitigations

- Potential closure/purity violations surfaced by compiler → fix locally.
- Third-party components with unusual patterns → isolate and exclude if necessary (none identified currently).

## References

- Next.js `reactCompiler` docs: <https://nextjs.org/docs/app/api-reference/config/next-config-js/reactCompiler>
- React Compiler overview: <https://react.dev/learn/react-compiler/introduction>
