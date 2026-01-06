# Server-Only Modules

Server-only modules live under `src/server/*`.

Conventions (see ADR-0069 / SPEC-0100):
- Database access must be server-only.
- Server Actions should be co-located in `src/app/**/actions.ts` or `src/lib/*/actions.ts`.
- Cached reads should live under `src/server/queries/*`.
- Route Handlers (`src/app/api/**/route.ts`) should stay thin and delegate into server-only modules.
