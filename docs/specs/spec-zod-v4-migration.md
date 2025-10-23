# Spec: Zod v3 -> v4 Migration (Planned Branch)

Owner: Frontend Platform
Status: Planned
Last updated: 2025-10-23

## Objective

Migrate all schemas and resolver integrations to Zod v4 and the latest `@hookform/resolvers`.

## Strategy

- Work in a branch `feat/zod-v4` to avoid blocking other tasks.
- Sequence: upgrade deps → codemod/transform common patterns → fix form resolvers → update custom validation utilities.

## Implementation Checklist

Dependencies

- [ ] Upgrade `zod` to v4 and `@hookform/resolvers` to a compatible version.

Code changes

- [ ] Replace deprecated Zod APIs; adjust import/typing changes.
- [ ] Update all `zodResolver(schema)` call sites where types changed.
- [ ] Re-run type-check and fix cascading form types.

Validation

- [ ] Run unit tests and e2e on form-heavy screens.

Docs

- [ ] Add migration notes to `docs/developers/` and link from ADR index if needed.
