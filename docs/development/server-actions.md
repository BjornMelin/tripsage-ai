# Server Components and Server Actions Guide

React Server Components (RSC) and Server Actions patterns for TripSage.

## Server vs Client Components

### Decision Tree

| Use Case | Component Type | Directive |
|----------|---------------|-----------|
| Data fetching, DB queries | Server | None (default) |
| Static content, layouts | Server | None (default) |
| Forms, user input | Client | `"use client"` |
| Interactivity, event handlers | Client | `"use client"` |
| Zustand stores, hooks | Client | `"use client"` |
| Browser APIs (localStorage, etc.) | Client | `"use client"` |

### File Structure

```typescript
// Server Component (default) - no directive needed
// src/app/(dashboard)/trips/page.tsx

import { createServerSupabase } from "@/lib/supabase/server";

export default async function TripsPage() {
  const supabase = await createServerSupabase();
  const { data: trips } = await supabase.from("trips").select("*");

  return <TripList trips={trips} />;
}
```

```typescript
// Client Component - requires directive
// src/components/features/trips/trip-form.tsx

/**
 * @fileoverview Trip creation form component.
 */

"use client";

import { useZodForm } from "@/hooks/use-zod-form";
// ... form implementation
```

## Server Actions

### File Organization

| Location | Use Case |
|----------|----------|
| `src/app/(route)/actions.ts` | Route-specific actions |
| `src/lib/auth/actions.ts` | Shared auth actions |
| `src/lib/*/actions.ts` | Domain-specific shared actions |

### Action Implementation Pattern

```typescript
// src/app/(dashboard)/trips/actions.ts
"use server";

import "server-only";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { tripCreateSchema } from "@schemas/trips";
import { createServerSupabase } from "@/lib/supabase/server";

export async function createTripAction(data: TripCreateData) {
  // 1. Validate
  const result = tripCreateSchema.safeParse(data);
  if (!result.success) throw new Error("Validation failed");

  // 2. Auth check
  const supabase = await createServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error("Auth required");

  // 3. Mutate
  const { data: trip, error } = await supabase
    .from("trips")
    .insert({ ...result.data, user_id: user.id })
    .select("id, title")
    .single();
  if (error) throw new Error("Insert failed");

  // 4. Revalidate
  revalidatePath("/trips");
  return trip;
}

export async function deleteTripAction(tripId: string): Promise<never> {
  const supabase = await createServerSupabase();
  await supabase.from("trips").delete().eq("id", tripId);
  revalidatePath("/trips");
  redirect("/trips");
}
```

### Key Requirements

1. **Directives:** Both `"use server"` and `import "server-only"` at file top
2. **Validation:** Always validate with Zod before processing
3. **Auth:** Use `createServerSupabase()` for authenticated client
4. **Returns:** Only serializable data (no Supabase client, no functions)
5. **Errors:** Throw descriptive errors; client receives error message
6. **Revalidation:** Call `revalidatePath()` or `revalidateTag()` after mutations

## Calling Server Actions

### From Client Components

```typescript
"use client";

import { createTripAction } from "./actions";
import { useZodForm } from "@/hooks/use-zod-form";

function TripForm() {
  const form = useZodForm({ schema: tripFormSchema });

  const onSubmit = form.handleSubmitSafe(async (data) => {
    const trip = await createTripAction(data);
    router.push(`/trips/${trip.id}`);
  });

  return <form onSubmit={onSubmit}>{/* fields */}</form>;
}
```

### With useActionState (Progressive Enhancement)

For forms that work without JavaScript:

```typescript
"use client";

import { useActionState } from "react";

const [state, formAction, isPending] = useActionState(
  async (_prev, formData: FormData) => {
    try {
      await createTripAction(Object.fromEntries(formData));
      return { success: true };
    } catch (e) {
      return { error: e instanceof Error ? e.message : "Failed" };
    }
  },
  {}
);

// Use: <form action={formAction}> with native inputs
// state.error / state.success available after submission
```

### Direct FormData Actions

For simpler forms without RHF:

```typescript
// actions.ts
"use server";

import { z } from "zod";

const feedbackSchema = z.strictObject({
  message: z.string().min(10).max(1000),
  rating: z.coerce.number().int().min(1).max(5),
});

export async function submitFeedbackAction(formData: FormData) {
  const data = Object.fromEntries(formData.entries());
  const validation = feedbackSchema.safeParse(data);

  if (!validation.success) {
    return { error: validation.error.message };
  }

  // ... save feedback
  return { success: true };
}
```

## Revalidation Patterns

### Path Revalidation

```typescript
import { revalidatePath } from "next/cache";

// Revalidate specific page
revalidatePath("/trips");

// Revalidate with layout
revalidatePath("/trips", "layout");

// Revalidate dynamic route
revalidatePath(`/trips/${tripId}`);
```

### Tag Revalidation

```typescript
// In data fetching:
const trips = await fetch("/api/trips", { next: { tags: ["trips"] } });

// In action after mutation:
import { revalidateTag } from "next/cache";
revalidateTag("trips");
```

## Error Handling

### Client-Side Error Handling

```typescript
"use client";

import { useTransition } from "react";

const [isPending, startTransition] = useTransition();
const [error, setError] = useState<string | null>(null);

const handleDelete = () => {
  startTransition(async () => {
    try {
      await deleteTripAction(tripId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  });
};
// isPending for loading state, error for display
```

### Server-Side Logging

Always log errors server-side before throwing:

```typescript
export async function riskyAction(data: unknown) {
  try {
    // ... operation
  } catch (error) {
    logger.error("Operation failed", { error, data });
    throw new Error("Operation failed. Please try again.");
  }
}
```

## Testing Server Actions

See [Testing Guide - Server Actions Section](./testing.md#server-actions) for:

- Mocking `createServerSupabase`
- Mocking `next/navigation`
- Testing with FormData
- Error scenario testing
