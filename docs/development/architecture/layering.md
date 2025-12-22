# Layering Policy

This policy defines architectural layers and allowed dependency directions. It
keeps domain logic portable, avoids UI/framework coupling, and makes refactors
safer.

## Layers

### 1) Domain (`src/domain`, `@domain/*`, `@schemas/*`)

- Core business logic, domain services, and schemas.
- Should be framework-agnostic and stable.
- `src/domain/schemas/**` is a leaf: schemas must not import `next/*`, `server-only`, or `@/lib/**` (schemas may depend only on Zod and other schemas).

### 2) Lib/Infra (`src/lib`, `@/*`)

- Infrastructure and platform adapters (Supabase, Redis, telemetry, env, HTTP).
- Utilities that are not domain-specific.

### 3) AI (`src/ai`, `@ai/*`)

- AI SDK tools, agents, prompts, model registry.
- Should depend on Domain + Lib/Infra, not on App.

### 4) App (`src/app`, `src/components`, `src/hooks`, `src/stores`, `src/styles`)

- Next.js routes, UI components, hooks, stores, and application wiring.
- Top of the dependency graph.

## Allowed Import Directions

| From \\ To | Domain | Lib/Infra | AI | App |
| --- | --- | --- | --- | --- |
| **Domain** | ✅ | ⚠️ (legacy only) | ❌ | ❌ |
| **Lib/Infra** | ✅ | ✅ | ❌ | ❌ |
| **AI** | ✅ | ✅ | ✅ | ❌ |
| **App** | ✅ | ✅ | ✅ | ✅ |

Notes:
- Domain **must not** import `next/*` or anything under `src/app/**`.
- Domain importing Lib/Infra is legacy and should be burned down over time.
- Domain schemas (`src/domain/schemas/**`) **must not** import Lib/Infra at all.
- Server/Client boundaries still apply: client components must not import server-only modules.

## Examples

Allowed:
- `src/ai/tools/server/accommodations.ts` → `@domain/accommodations/service`
- `src/app/api/trips/route.ts` → `@domain/trips/service`, `@/lib/telemetry/span`
- `src/app/agents/page.tsx` → `@ai/agents/chat-agent`

Forbidden:
- `src/domain/trips/service.ts` → `next/headers`
- `src/domain/search/service.ts` → `@/app/api/search/route`
- `src/lib/supabase/server.ts` → `@ai/tools/server/web-search`

## Enforcement

CI enforces boundaries via `scripts/check-boundaries.mjs`:
- Domain → App/Next imports are blocked.
- Domain schemas → Lib/Infra/Next/`server-only` imports are blocked.
- Client components importing server-only modules are blocked.

To prevent *new* Domain → Lib/Infra coupling while burning down legacy imports,
CI also runs `scripts/check-no-new-domain-infra-imports.mjs` (diff-based; allow only with an inline `domain-infra-ok:` justification marker).

Legacy exceptions live in `DOMAIN_IMPORT_ALLOWLIST` within `scripts/check-boundaries.mjs`.
Add an entry only with a short rationale and a burn-down plan.
