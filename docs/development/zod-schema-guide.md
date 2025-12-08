# Zod Schema Reference

Zod v4 schemas for TripSage AI validation. Provides compile-time types and runtime validation in one declarative API.

## Organization

**Domain Schemas** (`frontend/src/domain/schemas/`): Core business entities independent of AI  
**AI Tool Schemas** (`frontend/src/ai/tools/schemas/`): Vercel AI SDK v6 tool input/output contracts  
**Registry** (`frontend/src/domain/schemas/registry.ts`): Shared primitives and transforms

### Canonical Type Sources

**Single Source of Truth:** Each domain entity has one canonical schema and type definition in `@schemas/*`. Other modules import and re-export for convenience, but the schema file is authoritative.

**Example - Trip Types:**

- **Canonical:** `@schemas/trips` exports `storeTripSchema` and `UiTrip` type
- **Store:** `@/stores/trip-store` imports `UiTrip` and re-exports as `Trip`
- **Hooks:** `@/hooks/use-trips` imports `UiTrip` and re-exports as `Trip`
- **Database:** `@/lib/supabase/database.types` has `Trip = Tables<"trips">` (raw DB row type, separate from UI type)
- **Mappers:** `@/lib/trips/mappers` uses `UiTrip` from `@schemas/trips` for DB↔UI conversion

**Rule:** Always import the canonical type from `@schemas/*` when possible. Store/hook re-exports are convenience aliases only.  

### Directory Structure

```text
frontend/src/domain/schemas/
├── registry.ts        # Shared primitives and transforms
├── chat.ts            # Messages and conversations
├── budget.ts          # Financial entities
└── ...

frontend/src/ai/tools/schemas/
├── tools.ts           # Core tool schemas
├── web-search.ts      # Web search validation
├── planning.ts        # Trip planning AI schemas
└── ...
```

### File Structure

Use clear section headers:

```typescript
// ===== CORE SCHEMAS =====
// ===== FORM SCHEMAS =====
// ===== API SCHEMAS =====
// ===== UTILITY FUNCTIONS =====
```

## Export Patterns

Pair schema and type together in the same module (no central type barrel):

```typescript
/** Zod schema for user profile data with validation rules. */
export const userSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  name: z.string().min(1).max(100),
});

/** TypeScript type for user profile data. */
export type User = z.infer<typeof userSchema>;
```

**Why?** Keeps schema and type co-located for better maintainability and IDE support.

**Avoid:** Collecting exports at bottom, separating schema/type definitions, type-only exports.

## Documentation & Naming

Document all top-level exports following Google TypeScript Style Guide:

```typescript
/**
 * Zod schema for chat messages with tool calls, attachments, and metadata.
 * Validates message structure, content requirements, and attachment constraints.
 * Used for both API communication and client-side state management.
 */
export const messageSchema = z.strictObject({...});
export type Message = z.infer<typeof messageSchema>;
```

**Include:** Purpose, constraints, usage, business rules.
**Naming:** Schema constants use `camelCase`, types use `UpperCamelCase`.

## Registry Usage

Shared validation patterns in `frontend/src/domain/schemas/registry.ts`:

```typescript
// Use @schemas/* alias for all schema imports
import { primitiveSchemas, transformSchemas, refinedSchemas } from "@schemas/registry";

// Primitives: uuid, email, url, isoDateTime, isoCurrency, positiveNumber, percentage
const userId = primitiveSchemas.uuid.parse("123e4567-e89b-12d3-a456-426614174000");
const email = primitiveSchemas.email.parse("user@example.com");

// Transforms: trimmedString, lowercaseEmail, normalizedUrl
const trimmed = transformSchemas.trimmedString.parse("  hello  ");
const normalizedEmail = transformSchemas.lowercaseEmail.parse("Test@Example.COM");

// Refined: futureDate, adultAge, strongPassword
const futureDate = refinedSchemas.futureDate.parse("2025-12-31T12:00:00Z");
const password = refinedSchemas.strongPassword.parse("Test123!Password");
```

## Form Schema Patterns

Schemas for React Hook Form integration with Zod v4.

### Form vs API Schemas

Separate form schemas from API schemas when they differ:

```typescript
// @schemas/trips.ts

// ===== CORE SCHEMAS =====
export const tripSchema = z.strictObject({
  id: z.uuid(),
  title: z.string().min(3).max(200),
  destination: z.string().min(1),
  userId: z.uuid(),
  // ... other fields
});

// ===== FORM SCHEMAS =====
export const tripFormSchema = tripSchema.omit({ id: true, userId: true });
export type TripFormData = z.infer<typeof tripFormSchema>;
```

### Cross-Field Validation

Use `.refine()` with `path` to show errors on the correct field:

```typescript
export const dateRangeSchema = z.strictObject({
  checkIn: z.string().datetime(),
  checkOut: z.string().datetime(),
}).refine(
  (data) => new Date(data.checkOut) > new Date(data.checkIn),
  { error: "Checkout must be after check-in", path: ["checkOut"] }
);
```

Multi-field conditional validation:

```typescript
const paymentSchema = z.strictObject({
  method: z.enum(["card", "bank"]),
  cardNumber: z.string().nullable(),
  bankAccount: z.string().nullable(),
}).refine(
  (d) => (d.method === "card" ? !!d.cardNumber : !!d.bankAccount),
  { error: "Payment details required", path: ["method"] }
);
```

### RHF Integration

Schemas work directly with `zodResolver`:

```typescript
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { tripFormSchema, type TripFormData } from "@schemas/trips";

const form = useForm<TripFormData>({
  resolver: zodResolver(tripFormSchema),
  mode: "onChange",
  defaultValues: { title: "", destination: "" },
});
```

Or use the `useZodForm` hook which applies the resolver internally:

```typescript
import { useZodForm } from "@/hooks/use-zod-form";
import { tripFormSchema } from "@schemas/trips";

const form = useZodForm({
  schema: tripFormSchema,
  defaultValues: { title: "", destination: "" },
});
```

### Transforms for Form Input

Use transforms for common input normalization:

```typescript
export const searchFormSchema = z.strictObject({
  query: z.string().transform((s) => s.trim()),
  email: z.string().email().transform((s) => s.toLowerCase()),
  maxPrice: z.string().transform((s) => Number(s) || 0),
});
```

Note: `Number(s) || 0` collapses empty or invalid input to `0`, hiding the difference between “no value” and an explicit zero. When that distinction matters, use a nullable transform instead (e.g., `maxPrice: z.string().transform((s) => { const n = Number(s.trim()); return Number.isFinite(n) ? n : null; }).nullable()`), and treat `null` downstream as “no max price” or convert it to a default before submitting.

### Partial Schemas for Wizard Steps

Use `.pick()` for multi-step forms:

```typescript
// Step schemas derived from full schema
export const step1Schema = tripSchema.pick({ title: true, destination: true });
export const step2Schema = tripSchema.pick({ startDate: true, endDate: true });
export const step3Schema = tripSchema.pick({ budget: true, travelers: true });
```

## AI Tool Schemas

Vercel AI SDK v6 tool schemas require specific patterns for reliable LLM function calling.

For tool creation patterns with guardrails (caching, rate limiting, telemetry), see [AI Tools Guide](ai-tools.md).

**Requirements:**

- `z.strictObject()` for tool inputs
- `.describe()` on all fields for LLM comprehension
- `.nullable()` instead of `.optional()` for OpenAI strict mode

```typescript
// Tool Input Schema
export const toolInputSchema = z.strictObject({
  field: z.string().describe("Field description for LLM"),
  optionalField: z.number().nullable().describe("Nullable field for strict mode"),
});

// Tool Output Schema
export const toolOutputSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("success"), data: z.unknown() }),
  z.object({ type: z.literal("error"), message: z.string() }),
]);
```

**Server vs Client Tools:**

- **Server** (`frontend/src/ai/tools/server/`): External APIs, `import 'server-only'`, secrets access
- **Client** (`frontend/src/ai/tools/client/`): UI interactions, no external APIs
- **Patterns**: Query tools (Server), Action tools (Server), UI tools (Client)

### Using Schemas

```typescript
// Form validation
export const userFormSchema = z.object({
  email: transformSchemas.lowercaseEmail.max(255),
  password: refinedSchemas.strongPassword,
  userId: primitiveSchemas.uuid,
});

// API validation
export const apiRequestSchema = z.object({
  id: primitiveSchemas.uuid,
  email: primitiveSchemas.email,
  amount: primitiveSchemas.positiveNumber,
});

// Error handling
const result = schema.safeParse(data);
if (!result.success) {
  result.error.issues.forEach(issue =>
    console.log(`${issue.path.join(".")}: ${issue.message}`)
  );
}
```

## AI SDK v6 & Zod v4 Patterns

### Tool Definition

```typescript
import { tool } from "ai";

export const webSearchTool = tool({
  description: "Search the web for current information",
  parameters: webSearchSchema,
  execute: async (args) => {
    // Use temperature: 0 for deterministic tool outputs
    return await callAIWithTool({ ...args, temperature: 0 });
  },
});
```

**Temperature:** Tool calls use `temperature: 0`, creative tasks use `temperature: 0.7-1.0`

**Zod v4 Migration:** `z.iso.datetime()` → `z.string().datetime()`, `message:` → `error:`, avoid deprecated APIs

## Testing & Checklist

**Test Locations:**

- `frontend/src/domain/schemas/__tests__/` - Domain schema tests
- `frontend/src/ai/tools/__tests__/` - AI tool schema tests

**Run Tests:** `pnpm test:run frontend/src/domain/schemas/__tests__ frontend/src/ai/tools/__tests__`

### Schema Creation Checklist

> **Note**: This is a reusable schema review template. Copy and complete for each new schema.

- [ ] Single responsibility principle
- [ ] Correct directory (domain vs AI tools)
- [ ] Clear section headers
- [ ] Server tools: `import 'server-only'`
- [ ] Standard export pattern (schema + type together)
- [ ] JSDoc documentation for all exports
- [ ] camelCase naming
- [ ] Registry primitives used
- [ ] `{ error: "..." }` for custom messages
- [ ] AI tools: `z.strictObject()`, `.describe()`, `.nullable()`
- [ ] Comprehensive tests and TypeScript compilation

### Templates

**Domain Schema:**

```typescript
// ===== CORE SCHEMAS =====
export const entitySchema = z.object({...});
export type Entity = z.infer<typeof entitySchema>;

// ===== FORM SCHEMAS =====
export const entityFormSchema = z.object({...});
export type EntityFormData = z.infer<typeof entityFormSchema>;
```

**AI Tool Schema:**

```typescript
// Tool input schema
export const toolInputSchema = z.strictObject({
  field: z.string().describe("Field description for LLM"),
});
```

## References

- [AI Tools Guide](ai-tools.md) - Tool creation with `createAiTool` factory and guardrails
- [Google TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html)
- [Zod v4 Documentation](https://zod.dev/)
