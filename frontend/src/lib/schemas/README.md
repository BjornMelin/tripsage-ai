# Zod Schema Registry

Shared Zod v4 schemas for validation and type inference.

For comprehensive documentation on using these schemas, see [Zod Schema Guide](../../../../../docs/developers/zod-schema-guide.md).

## Files

- `registry.ts` - Core registry with primitives, transforms, and refined schemas
- `api.ts` - API request/response schemas
- `forms.ts` - Form validation schemas
- `budget.ts` - Budget and expense schemas
- `validation.ts` - Validation error types and result schemas
- `__tests__/` - Schema validation and performance tests

## Quick Reference

```typescript
import { primitiveSchemas, transformSchemas, refinedSchemas } from "@/lib/schemas/registry";

// Basic validation
const email = primitiveSchemas.email.parse("user@example.com");
const url = primitiveSchemas.url.parse("https://example.com");

// Transforms
const normalizedEmail = transformSchemas.lowercaseEmail.parse("Test@Example.COM");

// Refined validation
const password = refinedSchemas.strongPassword.parse("Secure123!");
```
