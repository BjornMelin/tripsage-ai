# Zod Schema Guide

Shared Zod v4 schemas for validation. Contains primitives, transforms, and refined schemas.

## Overview

Common validation patterns defined as reusable Zod v4 schemas. All schemas use:

- **Top-level helpers**: `z.email()`, `z.uuid()`, `z.url()`, `z.iso.datetime()`
- **Unified error option**: `{ error: "..." }` format (not deprecated `message:`)
- **Registry primitives**: Shared schemas for common types

## Usage

### Importing Schemas

```typescript
import { primitiveSchemas, transformSchemas, refinedSchemas } from "@/lib/schemas/registry";
```

### Primitive Schemas

Basic validation patterns:

```typescript
// UUID validation
const userId = primitiveSchemas.uuid.parse("123e4567-e89b-12d3-a456-426614174000");

// Email validation
const email = primitiveSchemas.email.parse("user@example.com");

// URL validation
const url = primitiveSchemas.url.parse("https://example.com");

// ISO datetime validation
const timestamp = primitiveSchemas.isoDateTime.parse("2024-01-01T12:00:00Z");

// Non-empty string
const name = primitiveSchemas.nonEmptyString.parse("John Doe");

// Slug validation
const slug = primitiveSchemas.slug.parse("hello-world-123");

// IATA code (3 uppercase letters)
const airportCode = primitiveSchemas.iataCode.parse("JFK");

// ISO currency code (3 uppercase letters)
const currency = primitiveSchemas.isoCurrency.parse("USD");

// Positive number
const amount = primitiveSchemas.positiveNumber.parse(42);

// Percentage (0-100)
const discount = primitiveSchemas.percentage.parse(25);

// Non-negative number
const count = primitiveSchemas.nonNegativeNumber.parse(0);
```

### Transform Schemas

Schemas that normalize data:

```typescript
// Trim whitespace
const trimmed = transformSchemas.trimmedString.parse("  hello  ");
// Result: "hello"

// Lowercase email
const normalizedEmail = transformSchemas.lowercaseEmail.parse("Test@Example.COM");
// Result: "test@example.com"

// Normalized URL
const normalizedUrl = transformSchemas.normalizedUrl.parse("  HTTPS://EXAMPLE.COM  ");
// Result: "https://example.com"
```

### Refined Schemas

Schemas with complex validation logic:

```typescript
// Future date validation
const futureDate = refinedSchemas.futureDate.parse("2025-12-31T12:00:00Z");

// Adult age validation (18+)
const age = refinedSchemas.adultAge.parse(25);

// Strong password validation
const password = refinedSchemas.strongPassword.parse("Test123!Password");
// Validates: min 8 chars, max 128 chars, contains uppercase, lowercase, and numbers
```

## Using in Form Schemas

```typescript
import { z } from "zod";
import { primitiveSchemas, refinedSchemas, transformSchemas } from "@/lib/schemas/registry";

export const userFormSchema = z.object({
  email: transformSchemas.lowercaseEmail.max(255),
  password: refinedSchemas.strongPassword,
  userId: primitiveSchemas.uuid,
  website: primitiveSchemas.url.optional(),
});
```

## Using in API Schemas

```typescript
import { z } from "zod";
import { primitiveSchemas } from "@/lib/schemas/registry";

export const apiRequestSchema = z.object({
  id: primitiveSchemas.uuid,
  email: primitiveSchemas.email,
  timestamp: primitiveSchemas.isoDateTime,
  amount: primitiveSchemas.positiveNumber,
});
```

## Migration from Custom Validation

The custom validation utility (`validation.ts`) has been removed. Use Zod native patterns instead:

### Before (Custom Validation)

```typescript
import { validate, ValidationContext } from "@/lib/validation";

const result = validate(schema, data, ValidationContext.Form);
if (!result.success) {
  // Handle errors
}
```

### After (Zod Native)

```typescript
import { z } from "zod";

const result = schema.safeParse(data);
if (!result.success) {
  // Handle errors via result.error.issues
  result.error.issues.forEach((issue) => {
    console.error(`${issue.path.join(".")}: ${issue.message}`);
  });
}
```

## Error Handling

All schemas use Zod's unified error format:

```typescript
const result = primitiveSchemas.email.safeParse("invalid-email");
if (!result.success) {
  result.error.issues.forEach((issue) => {
    console.log({
      code: issue.code,
      path: issue.path,
      message: issue.message,
    });
  });
}
```

## Type Exports

The registry exports TypeScript types for common primitives:

```typescript
import type { Uuid, Email, Url, IsoDateTime, Timestamp } from "@/lib/schemas/registry";

const userId: Uuid = "123e4567-e89b-12d3-a456-426614174000";
const email: Email = "user@example.com";
const url: Url = "https://example.com";
const dateTime: IsoDateTime = "2024-01-01T12:00:00Z";
const timestamp: Timestamp = 1704110400;
```

## Performance

Performance benchmarks in `frontend/src/lib/schemas/__tests__/performance.test.ts`.

## Zod v4 Compliance

Schemas follow Zod v4 patterns:

- Top-level helpers (`z.email()`, not `z.string().email()`)
- Unified error option (`{ error: "..." }`, not `message:`)
- No deprecated APIs (`z.nativeEnum`, `z.record(schema)`, `.merge()`)
- Proper enum usage (`z.enum()`, not `z.nativeEnum()`)
- Two-argument `z.record()` (`z.record(keySchema, valueSchema)`)

## Schema Files

- `frontend/src/lib/schemas/registry.ts` - Core registry with primitives, transforms, and refined schemas
- `frontend/src/lib/schemas/api.ts` - API request/response schemas
- `frontend/src/lib/schemas/forms.ts` - Form validation schemas
- `frontend/src/lib/schemas/budget.ts` - Budget and expense schemas
- `frontend/src/lib/schemas/validation.ts` - Validation error types and result schemas

## Testing

Tests in `frontend/src/lib/schemas/__tests__/`:

- `registry.test.ts` - Schema validation tests
- `performance.test.ts` - Performance benchmarks

Run with:

```bash
pnpm test:run frontend/src/lib/schemas/__tests__
```
