# Code Standards

Coding guidelines and conventions for TripSage development.

## TypeScript Standards

### Import Paths

Follow the [Import Path Standards](import-paths.md) for all imports:

- Use `@schemas/*` for Zod schemas
- Use `@domain/*` for domain logic
- Use `@ai/*` for AI tooling
- Use `@/*` for generic src-root (lib, components, stores)
- Use relative imports (`./`, `../`) within the same feature directory

### Type Definitions

Use explicit types for all variables and function parameters:

```typescript
interface Trip {
  id: string;
  name: string;
  destinations: string[];
  status: 'planning' | 'booked' | 'completed';
}

function createTrip(tripData: Omit<Trip, 'id'>): Promise<Trip> {
  // Implementation
}
```

### React Components

Use functional components with proper typing:

```typescript
interface TripCardProps {
  trip: Trip;
  onEdit: (tripId: string) => void;
}

export function TripCard({ trip, onEdit }: TripCardProps) {
  return (
    <div>
      <h3>{trip.name}</h3>
      <button onClick={() => onEdit(trip.id)}>Edit</button>
    </div>
  );
}
```

### Custom Hooks

Follow the `use*` naming convention:

```typescript
function useTrips() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchTrips = async () => {
    setLoading(true);
    try {
      const response = await api.getTrips();
      setTrips(response.data);
    } finally {
      setLoading(false);
    }
  };

  return { trips, loading, fetchTrips };
}
```

### Zod Schema Organization

**Co-locate schemas by default**: Keep Zod schemas in the same file where they're primarily used (tool files, route handlers) to maintain context and keep validation logic close to execution.

**Extract to shared schemas when**:

- The same schema is consumed by ≥2 distinct modules (e.g., tool + UI form + route handler)
- You need strong schema versioning and stable import paths across multiple layers
- The schema exceeds ~150 LOC or has multiple discriminated unions that benefit from dedicated file organization

**Type definitions**: Import types directly from the defining schema module (`frontend/src/domain/schemas/<feature>.ts`) to keep schemas and inferred types co-located. Avoid separate type barrel files.

**Import paths**: Use `@schemas/*` alias for all schema imports. See [Import Paths](import-paths.md) for details.

**Best practices**:

- Use `.strict()` where inputs are external (user-provided or API responses)
- Prefer `.transform()` for normalization over ad-hoc post-processing
- Use cross-field `.refine`/`.superRefine` for invariants (e.g., checkout after checkin, non-negative price ranges)

Example:

```typescript
// frontend/src/ai/tools/server/accommodations.ts - schema co-located with tool
import { ACCOMMODATION_SEARCH_INPUT_SCHEMA } from "@schemas/accommodations";

const searchSchema = ACCOMMODATION_SEARCH_INPUT_SCHEMA.refine(
  (data) => new Date(data.checkout) > new Date(data.checkin), 
  "checkout must be after checkin"
);

export type AccommodationSearchParams = z.infer<typeof ACCOMMODATION_SEARCH_INPUT_SCHEMA>;
```

## Code Formatting

### TypeScript (Biome)

```bash
# Lint and fix issues
pnpm biome:fix

# Format code
pnpm format:biome

# Check only (no fixes)
pnpm biome:check
```

## Architecture Patterns

### Service Layer

Keep business logic in dedicated service classes with dependency injection:

```typescript
import { withTelemetrySpan } from "@/lib/telemetry/span";

interface ServiceDeps {
  db: DatabaseService;
  cache: CacheService;
  externalApi: ExternalApiService;
  rateLimiter?: RateLimiter;
}

export class TripService {
  constructor(private readonly deps: ServiceDeps) {}

  async createTrip(tripData: TripData, userId: string): Promise<Trip> {
    return await withTelemetrySpan(
      "trip.create",
      { attributes: { userId } },
      async () => {
        // Business logic here
      }
    );
  }
}
```

## Security Guidelines

### Input Validation

Validate all inputs using Zod schemas:

```typescript
import { z } from "zod";
import { primitiveSchemas } from "@schemas/registry";

const tripCreateSchema = z.strictObject({
  title: primitiveSchemas.nonEmptyString.max(200),
  destination: primitiveSchemas.nonEmptyString.max(200),
  startDate: z.string(),
  endDate: z.string(),
  budget: primitiveSchemas.nonNegativeNumber.optional(),
  travelers: primitiveSchemas.positiveNumber.int().default(1),
});

type TripCreateInput = z.infer<typeof tripCreateSchema>;
```

### Authentication

Use proper authentication patterns for Next.js API routes:

```typescript
import type { NextRequest } from "next/server";
import { withApiGuards } from "@/lib/api/factory";

export const GET = withApiGuards(async (req: NextRequest) => {
  // Authentication handled by withApiGuards
  // Protected route logic here
  return Response.json({ message: "Success" });
});
```

## Performance Guidelines

### Database Optimization

- Use indexes on frequently queried columns
- Avoid N+1 queries with eager loading
- Use connection pooling

### Caching Strategy

- Cache expensive operations
- Use appropriate TTL values
- Invalidate cache on data changes

### Async Best Practices

- Use async/await for all I/O operations
- Avoid blocking calls in async functions
- Use proper error handling with try/catch

## Code Review Checklist

> **Note**: This is a reusable PR review template. Copy and complete for each PR.

### Before Submitting

- [ ] Tests pass with >90% coverage
- [ ] Code is properly typed
- [ ] Linting passes without errors
- [ ] Documentation updated
- [ ] Security review completed

### During Review

- [ ] Code follows established patterns
- [ ] Error handling is appropriate
- [ ] Performance considerations addressed
- [ ] Security vulnerabilities checked
- [ ] Tests are meaningful and provide valuable insights
