# Zod Integration Guide for TripSage Frontend

This guide explains how to use Zod for schema validation throughout the TripSage frontend, mirroring the Pydantic approach used in the backend.

## Overview

Zod is a TypeScript-first schema validation library that provides:
- Runtime validation
- Static type inference
- Comprehensive error messages
- Transformation and refinement capabilities

## Why Zod?

Similar to how we use Pydantic in the backend:
- **Type Safety**: Automatically infers TypeScript types from schemas
- **Runtime Validation**: Validates data at runtime, catching errors early
- **Developer Experience**: Clear error messages and excellent IDE support
- **Integration**: Works seamlessly with React Hook Form, Next.js, and our API

## Schema Organization

```
src/lib/schemas/
├── common.ts       # Common schemas and utilities
├── trip.ts         # Trip-related schemas
├── flight.ts       # Flight booking schemas
├── accommodation.ts # Accommodation schemas
└── index.ts        # Export aggregation
```

## Basic Usage

### 1. Defining Schemas

```typescript
import { z } from 'zod';

// Define a schema (similar to Pydantic models)
export const TripCreateSchema = z.object({
  name: z.string().min(1, 'Trip name is required').max(100),
  destinations: z.array(z.string()).min(1, 'At least one destination is required'),
  startDate: z.string().refine((date) => {
    const parsed = new Date(date);
    return !isNaN(parsed.getTime()) && parsed > new Date();
  }, 'Start date must be in the future'),
  budget: z.object({
    currency: z.enum(['USD', 'EUR', 'GBP']).default('USD'),
    total: z.number().positive('Budget must be positive').optional(),
  }),
});

// Infer the TypeScript type
export type TripCreateInput = z.infer<typeof TripCreateSchema>;
```

### 2. Form Validation with React Hook Form

```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

export function TripForm() {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<TripCreateInput>({
    resolver: zodResolver(TripCreateSchema),
  });

  const onSubmit = async (data: TripCreateInput) => {
    // Data is already validated by Zod
    await createTrip(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('name')} />
      {errors.name && <span>{errors.name.message}</span>}
      
      <button type="submit">Create Trip</button>
    </form>
  );
}
```

### 3. API Route Validation

```typescript
import { createRouteHandler } from '@/lib/validation/route-handler';

export const POST = createRouteHandler({
  body: TripCreateSchema,
  response: TripResponseSchema,
  handler: async ({ body }) => {
    // Body is validated and typed
    const trip = await createTrip(body);
    return { success: true, data: trip };
  },
});
```

### 4. Server Actions with Validation

```typescript
'use server';

import { createServerAction } from '@/lib/validation/server-actions';

export const createTrip = createServerAction(
  TripCreateSchema,
  async (data) => {
    // Data is validated
    const trip = await db.trip.create({ data });
    return trip;
  }
);
```

## Advanced Patterns

### 1. Custom Validation

```typescript
const EmailSchema = z.string().email().refine(
  async (email) => {
    const exists = await checkEmailExists(email);
    return !exists;
  },
  { message: 'Email already exists' }
);
```

### 2. Conditional Validation

```typescript
const FlightSearchSchema = z.object({
  tripType: z.enum(['one-way', 'round-trip']),
  returnDate: z.string().optional(),
}).refine((data) => {
  if (data.tripType === 'round-trip' && !data.returnDate) {
    return false;
  }
  return true;
}, {
  message: 'Return date is required for round trips',
  path: ['returnDate'],
});
```

### 3. Transform Data

```typescript
const DateSchema = z.string().transform((str) => new Date(str));

const PriceSchema = z.number().transform((val) => 
  Math.round(val * 100) / 100 // Round to 2 decimal places
);
```

### 4. Partial and Extended Schemas

```typescript
// Similar to Pydantic's model inheritance
const TripSchema = TripCreateSchema.extend({
  id: z.string().uuid(),
  userId: z.string().uuid(),
  createdAt: z.date(),
  updatedAt: z.date(),
});

// Partial schema for updates
const TripUpdateSchema = TripCreateSchema.partial();
```

## Error Handling

### 1. Format Zod Errors

```typescript
export const formatZodError = (error: z.ZodError): ErrorResponse => {
  const errors = error.errors.map((err) => ({
    field: err.path.join('.'),
    message: err.message,
  }));
  
  return {
    success: false,
    error: {
      code: 'VALIDATION_ERROR',
      message: 'Validation failed',
      details: errors,
    },
  };
};
```

### 2. Display Errors in UI

```typescript
function FormField({ error, ...props }) {
  return (
    <div>
      <input {...props} />
      {error && (
        <span className="text-red-500 text-sm">{error.message}</span>
      )}
    </div>
  );
}
```

## Best Practices

### 1. Centralize Schemas

Keep all schemas in a central location (`src/lib/schemas/`) for reusability:

```typescript
// src/lib/schemas/index.ts
export * from './trip';
export * from './flight';
export * from './accommodation';
export * from './common';
```

### 2. Use Type Inference

Always use `z.infer` to get TypeScript types:

```typescript
// Good
type Trip = z.infer<typeof TripSchema>;

// Bad
interface Trip {
  // Duplicating schema definition
}
```

### 3. Compose Schemas

Build complex schemas from simpler ones:

```typescript
const AddressSchema = z.object({
  street: z.string(),
  city: z.string(),
  country: z.string(),
});

const AccommodationSchema = z.object({
  name: z.string(),
  location: AddressSchema, // Reuse schema
});
```

### 4. Custom Error Messages

Provide clear, user-friendly error messages:

```typescript
const PasswordSchema = z.string()
  .min(8, 'Password must be at least 8 characters')
  .regex(/[A-Z]/, 'Password must contain an uppercase letter')
  .regex(/[0-9]/, 'Password must contain a number');
```

### 5. Validate at the Edge

Validate data as early as possible:
- Form inputs (client-side)
- API routes (server-side)
- Server actions
- External API responses

## Integration with Backend

### 1. Shared Schema Patterns

Mirror backend Pydantic models:

```python
# Backend (Pydantic)
class TripCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    destinations: List[str] = Field(..., min_items=1)
    start_date: datetime
    budget: Optional[Budget] = None
```

```typescript
// Frontend (Zod)
const TripCreateSchema = z.object({
  name: z.string().min(1).max(100),
  destinations: z.array(z.string()).min(1),
  startDate: z.string(),
  budget: BudgetSchema.optional(),
});
```

### 2. API Response Validation

Validate backend responses:

```typescript
const fetchTrip = async (id: string) => {
  const response = await fetch(`/api/trips/${id}`);
  const data = await response.json();
  
  // Validate the response
  return TripSchema.parse(data);
};
```

## Testing

### 1. Test Schema Validation

```typescript
import { describe, it, expect } from 'vitest';

describe('TripCreateSchema', () => {
  it('validates a valid trip', () => {
    const validTrip = {
      name: 'European Tour',
      destinations: ['Paris', 'Rome'],
      startDate: '2025-06-01',
      budget: { currency: 'EUR', total: 5000 },
    };
    
    expect(() => TripCreateSchema.parse(validTrip)).not.toThrow();
  });
  
  it('rejects invalid data', () => {
    const invalidTrip = {
      name: '', // Empty name
      destinations: [], // Empty array
    };
    
    expect(() => TripCreateSchema.parse(invalidTrip)).toThrow();
  });
});
```

### 2. Mock Data Generation

```typescript
import { faker } from '@faker-js/faker';

export const mockTripData = (): TripCreateInput => ({
  name: faker.location.city() + ' Trip',
  destinations: [faker.location.city(), faker.location.city()],
  startDate: faker.date.future().toISOString(),
  endDate: faker.date.future().toISOString(),
  budget: {
    currency: 'USD',
    total: faker.number.int({ min: 1000, max: 10000 }),
  },
});
```

## Performance Considerations

1. **Lazy Loading**: Import schemas only when needed
2. **Memoization**: Cache parsed schemas for repeated use
3. **Async Validation**: Use `.parseAsync()` for complex validations
4. **Selective Validation**: Validate only changed fields in forms

## Migration from Untyped Code

1. Start with critical user inputs (forms, API routes)
2. Gradually add schemas to existing code
3. Use `.parse()` to validate and type existing data
4. Replace interface definitions with inferred types

## Conclusion

Zod provides a robust validation layer for the TripSage frontend, ensuring data integrity and type safety throughout the application. By following these patterns and best practices, we maintain consistency with our backend validation approach while leveraging TypeScript's type system for a superior developer experience.