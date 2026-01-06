Feature-first modules live under `src/features/<feature>/...`.

Conventions (see ADR-0069):
- Keep UI and feature-specific logic co-located per feature.
- Keep server-only code out of Client Components.
- Keep `src/components/ui/*` reserved for shadcn/ui primitives only.
