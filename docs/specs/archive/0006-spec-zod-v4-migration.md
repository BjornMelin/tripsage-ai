# SPEC-0006: Zod v3 -> v4 Migration (Planned Branch)

Status: Completed
Last updated: 2025-10-23

## Objective

Migrate all schemas and resolver integrations to Zod v4 and the latest `@hookform/resolvers`.

## Strategy

Performed incrementally in-place:

1. Upgraded dependencies to Zod v4 and @hookform/resolvers v5.
2. Verified resolver import and runtime by adding a small smoke test.
3. Left form schemas unchanged (no deprecated APIs were present).

## Implementation Checklist

Dependencies

- [x] Upgrade `zod` to v4 and `@hookform/resolvers` to v5.

Code changes

- [x] No deprecated APIs were detected in the codebase; imports remain `import { z } from "zod"`.
- [x] Re-ran type-check; no schema changes required.

Validation

- [x] Added smoke test to ensure resolver + v4 interop:
  - `frontend/src/hooks/__tests__/use-chat-ai.test.tsx` (already in suite)
  - `frontend/src/lib/__tests__/zod-v4-resolver.test.tsx` (new; basic resolver sanity)
  - Targeted test run: `pnpm vitest run src/lib/__tests__/zod-v4-resolver.test.tsx`

Docs

- [x] This spec updated; no developer-facing schema changes required.
