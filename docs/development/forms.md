# Forms and Validation Guide

React Hook Form (RHF) integration with Zod v4 for TripSage forms.

## Hooks

### useZodForm

Full-featured form hook with validation, error handling, and telemetry.

**Location:** `@/hooks/use-zod-form`

```typescript
import { useZodForm } from "@/hooks/use-zod-form";
import { tripFormSchema } from "@schemas/trips";

const form = useZodForm({
  schema: tripFormSchema,
  defaultValues: { title: "", destination: "" },
});

// Submit with built-in validation
const onSubmit = form.handleSubmitSafe(async (data) => {
  await saveTrip(data);
});

// Use with Form components (see UI Components section below)
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `schema` | `z.ZodType<T>` | required | Zod schema for validation |
| `defaultValues` | `DefaultValues<T>` | `{}` | Initial form values |
| `validateMode` | `"onChange" \| "onBlur" \| "onSubmit"` | `"onChange"` | When to validate |
| `reValidateMode` | `"onChange" \| "onBlur" \| "onSubmit"` | `"onChange"` | When to re-validate after error |
| `transformSubmitData` | `(data: T) => T` | - | Transform data before submission |
| `onValidationError` | `(errors) => void` | - | Callback on validation failure |
| `onSubmitSuccess` | `(data) => void` | - | Callback on successful submission |
| `onSubmitError` | `(error) => void` | - | Callback on submission error |

**Return Values:**

| Property | Description |
|----------|-------------|
| `handleSubmitSafe` | Safe submit handler with validation |
| `validateField(name, value)` | Validate single field |
| `validateAllFields()` | Validate entire form |
| `isFieldValid(name)` | Check if field is valid |
| `getFieldError(name)` | Get field error message |
| `hasAnyErrors` | Boolean if form has errors |
| `isFormComplete` | Boolean if form passes validation |
| `getCleanData()` | Get parsed/validated data |
| `resetToDefaults()` | Reset form to default values |
| `validationState` | `{ isValidating, lastValidation, validationErrors }` |

### useSearchForm

Thin wrapper for search-specific forms. Simpler API for quick search implementations.

**Location:** `@/components/features/search/common/use-search-form`

```typescript
import { useSearchForm } from "@/components/features/search/common/use-search-form";
import { HotelSearchForm } from "@/components/features/search/forms/hotel-search-form";
import { hotelSearchSchema } from "@schemas/search";

function HotelSearch() {
  const form = useSearchForm(hotelSearchSchema, {
    destination: "",
    checkIn: "",
    checkOut: "",
  });

  return <Form {...form}>{/* fields */}</Form>;
}
```

### useZodFormWizard

Multi-step form wizard with step validation.

**Location:** `@/hooks/use-zod-form`

```typescript
import { useZodFormWizard } from "@/hooks/use-zod-form";

const steps = [
  { name: "basics", title: "Basic Info", schema: basicInfoSchema },
  { name: "dates", title: "Travel Dates", schema: datesSchema },
  { name: "preferences", title: "Preferences", schema: preferencesSchema },
];

const wizard = useZodFormWizard(steps, tripFinalSchema);

// Access wizard state
wizard.currentStep;        // 0-based index
wizard.progress;           // percentage complete
wizard.isFirstStep;        // boolean
wizard.isLastStep;         // boolean

// Navigation
wizard.nextStep();         // validate current step, advance if valid
wizard.previousStep();     // go back
wizard.submitWizard();     // validate all, return final data
```

## UI Components

Import from `@/components/ui/form`:

```typescript
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
} from "@/components/ui/form";
```

**Component Structure:**

```tsx
<Form {...form}>
  <FormField
    control={form.control}
    name="fieldName"
    render={({ field }) => (
      <FormItem>
        <FormLabel>Label</FormLabel>
        <FormControl>
          <Input {...field} />
        </FormControl>
        <FormDescription>Optional helper text</FormDescription>
        <FormMessage /> {/* Shows validation error */}
      </FormItem>
    )}
  />
</Form>
```

## Validation Patterns

### Cross-Field Validation

Use `.refine()` with `path` to show error on the correct field:

```typescript
const dateRangeSchema = z.strictObject({
  checkIn: z.string(),
  checkOut: z.string(),
}).refine(
  (data) => new Date(data.checkOut) > new Date(data.checkIn),
  { error: "Checkout must be after check-in", path: ["checkOut"] }
);
```

### Async Validation

Use `useAsyncZodValidation` for debounced async validation:

```typescript
import { useAsyncZodValidation } from "@/hooks/use-zod-form";

const { validate, isValidating, errors } = useAsyncZodValidation(
  emailUniqueSchema,
  300 // debounce ms
);

// Call validate(data) on input changes
```

## Submission Patterns

### Safe Submit with Telemetry

Wrap async handlers with telemetry for observability:

```typescript
import { withClientTelemetrySpan } from "@/lib/telemetry/client";

const onSubmit = form.handleSubmitSafe(async (data) => {
  await withClientTelemetrySpan("trip.create", async () => {
    await createTrip(data);
  });
});
```

### AbortController for Async Operations

Cancel in-flight requests on unmount or re-submit:

```typescript
const abortRef = useRef<AbortController | null>(null);

const onSubmit = form.handleSubmitSafe(async (data) => {
  abortRef.current?.abort();                         // Cancel previous
  abortRef.current = new AbortController();

  try {
    await fetchResults(data, { signal: abortRef.current.signal });
  } catch (e) {
    if (e instanceof Error && e.name === "AbortError") return; // Silent
    throw e;
  }
});

useEffect(() => () => abortRef.current?.abort(), []); // Cleanup on unmount
```

### Server Action Integration

Call server actions from form submission:

```typescript
import { submitHotelSearch } from "./actions";

const onSubmit = form.handleSubmitSafe(async (data) => {
  const validated = await submitHotelSearch(data);
  router.push(`/search/results?${new URLSearchParams(validated)}`);
});
```

## Schema Organization

Form schemas should be co-located with domain schemas. See [Form Schema Patterns](./zod-schema-guide.md#form-schema-patterns) for schema design examples that pair with these hooks.

```typescript
// @schemas/trips.ts

// ===== CORE SCHEMAS =====
export const tripSchema = z.strictObject({
  id: z.uuid(),
  title: z.string().min(1).max(200),
  // ...
});

// ===== FORM SCHEMAS =====
export const tripFormSchema = tripSchema.omit({ id: true });
export type TripFormData = z.infer<typeof tripFormSchema>;
```

## Testing Forms

See [Testing Guide - Forms Section](./testing.md#forms) for:

- Validation error testing
- Submission testing
- Wizard navigation testing
