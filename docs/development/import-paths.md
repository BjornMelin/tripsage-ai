# Import Path Standards

TypeScript import path conventions for the TripSage frontend. Ensures consistent, maintainable code organization.

## Path Aliases

Four semantic aliases map to architectural boundaries:

| Alias | Maps To | Use For |
|-------|---------|---------|
| `@schemas/*` | `./src/domain/schemas/*` | All Zod/domain schemas (validation, DTOs, tool inputs) |
| `@domain/*` | `./src/domain/*` | Domain logic (accommodations, amadeus, types) |
| `@ai/*` | `./src/ai/*` | AI SDK tooling, models, helpers |
| `@/*` | `./src/*` | Generic src-root (lib, components, stores, hooks, app) |

## Usage Rules

### When to Use Aliases

**Use semantic aliases** (`@schemas/*`, `@domain/*`, `@ai/*`) when:

- Importing from outside your current feature slice
- Crossing architectural boundaries (e.g., lib → domain, app → ai)
- Importing schemas from anywhere in the codebase

**Use relative imports** (`./`, `../`) when:

- Importing within the same feature directory (e.g., `src/domain/amadeus/client.ts` → `./client-types.ts`)
- Files are in the same small feature tree
- The import path is short and clear (≤2 levels up)

### Examples

```typescript
// ✅ CORRECT: Schema import from anywhere
import { accommodationSchema } from "@schemas/accommodations";
import type { AccommodationSearchParams } from "@schemas/accommodations";

// ✅ CORRECT: Domain logic from outside domain
import { AccommodationsService } from "@domain/accommodations/service";
import type { CalendarEvent } from "@schemas/calendar";

// ✅ CORRECT: AI tooling from outside AI
import { createAiTool } from "@ai/lib/tool-factory";
import { resolveProvider } from "@ai/models/registry";

// ✅ CORRECT: Generic src-root imports
import { createServerSupabase } from "@/lib/supabase/server";
import { useAuthStore } from "@/stores/auth/auth-store";

// ✅ CORRECT: Relative imports within same feature
// In src/domain/amadeus/client.ts
import { ProviderError } from "@domain/accommodations/errors";
import { AMADEUS_DEFAULT_BASE_URL } from "./constants";

// ❌ INCORRECT: Using @/domain/ instead of @domain/
import { AccommodationsService } from "@/domain/accommodations/service";

// ❌ INCORRECT: Using @/ai/ instead of @ai/
import { createAiTool } from "@/ai/lib/tool-factory";

// ❌ INCORRECT: Using @/domain/schemas/ instead of @schemas/
import { accommodationSchema } from "@/domain/schemas/accommodations";
```

## Disallowed Patterns

These patterns are explicitly forbidden and will be flagged by linting:

- `@/domain/*` → Use `@domain/*` instead
- `@/ai/*` → Use `@ai/*` instead
- `@/domain/schemas/*` → Use `@schemas/*` instead

## Configuration

Path aliases are configured in:

- **TypeScript**: `frontend/tsconfig.json` → `compilerOptions.paths`
- **Vitest**: `frontend/vitest.config.ts` → `resolve.alias`
- **Next.js**: Automatically uses `tsconfig.json` paths

## Migration Checklist

When adding new imports:

1. Determine the architectural boundary:
   - Schema? → `@schemas/*`
   - Domain logic? → `@domain/*`
   - AI tooling? → `@ai/*`
   - Generic lib/components/stores? → `@/*`
2. Check if within same feature directory → use relative import
3. Verify the alias matches the target directory structure
4. Run `pnpm biome:check` to catch any violations

## Common Patterns

### Schema Imports

```typescript
// From domain schemas
import { accommodationSchema } from "@schemas/accommodations";
import type { AccommodationSearchParams } from "@schemas/accommodations";

// From AI tool schemas
import { webSearchInputSchema } from "@ai/tools/schemas/web-search";
```

### Domain Logic Imports

```typescript
// Service classes
import { AccommodationsService } from "@domain/accommodations/service";

// Domain types
import type { CalendarEvent, EventDateTime } from "@schemas/calendar";

// Domain utilities
import { ProviderError } from "@domain/accommodations/errors";
```

### AI Tooling Imports

```typescript
// Tool factories
import { createAiTool } from "@ai/lib/tool-factory";

// Provider registry
import { resolveProvider } from "@ai/models/registry";

// Tool schemas
import { travelAdvisoryInputSchema } from "@ai/tools/schemas/travel-advisory";
```

### Generic Imports

```typescript
// Lib utilities
import { createServerSupabase } from "@/lib/supabase/server";
import { secureUuid } from "@/lib/security/random";

// Components
import { Button } from "@/components/ui/button";

// Stores
import { useAuthStore } from "@/stores/auth/auth-store";

// Hooks
import { useChat } from "@/hooks/use-chat";
```

## Troubleshooting

### Import Not Resolved

1. Verify the alias exists in `tsconfig.json`
2. Check the file path matches the alias mapping
3. Restart TypeScript server in your IDE
4. Run `pnpm type-check` to see detailed errors

### Wrong Alias Used

1. Check this guide for the correct alias
2. Run `pnpm biome:check` to find violations
3. Fix using the patterns above

### Relative vs Alias Confusion

- **Same directory or immediate parent?** → Use relative (`./`, `../`)
- **Crossing feature boundaries?** → Use semantic alias (`@schemas/*`, `@domain/*`, `@ai/*`)
- **Generic src-root?** → Use `@/*`
