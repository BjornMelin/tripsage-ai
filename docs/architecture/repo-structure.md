# Repo structure

## Why feature-first

Feature-first keeps ownership clear and prevents shared utility sprawl. It also reduces accidental client bundling of server-only code.

## Boundary rules

- `src/server/*` is server-only. No imports from client components.
- `src/features/*/server/*` is server-only (actions/queries/helpers for that feature).
- `src/components/ui/*` is shadcn/ui only. No business logic.
- Routes in `src/app/*` should be thin routing and composition only.

## Import rules (enforced by lint)

- Client components cannot import from `src/server/*`.
- Server actions cannot import UI.
- Route handlers must validate inputs and verify signatures where applicable.
