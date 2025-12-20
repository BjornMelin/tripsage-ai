# TripSage AI - Detailed Implementation Prompts

**Instructions**: Each prompt below is **completely independent** and can be run in a fresh Claude Code session. Copy the entire prompt text (including the markdown fence) into Claude Code. Each prompt includes:
- Exact files and line ranges to modify
- Investigation steps
- Implementation code with exact changes
- Verification/testing requirements
- Rollback procedures if needed

All prompts assume you have the CLAUDE.md and AGENTS.md context (automatically loaded in Claude Code for this repo).

---

## Prompt 1: Consolidate Route Handler Error Responses

**Task ID**: IMPL-001
**Category**: Code Duplication & Library Leverage
**Severity**: HIGH
**Effort**: Small
**Scope**: `src/app/api/**` (10-15 files affected, ~50 lines changed total)

**Dependencies**: None

---

```markdown
# Consolidate Route Handler Error Responses into Unified Helper

## Problem

Route handlers across `src/app/api/**` are inconsistently using `errorResponse()` from `@/lib/next/route-helpers`. Some handlers:
- Manually construct error objects instead of using the helper
- Duplicate error status code logic
- Have inconsistent error message formatting
- Don't properly set Content-Type headers

This violates AGENTS.md 5.1 which mandates: "No inline `NextResponse.json({ error })` — use `errorResponse()` from `@/lib/next/route-helpers`".

## Investigation Phase

1. **Audit current usage**:
   ```bash
   grep -r "NextResponse.json.*error" src/app/api/ | head -20
   grep -r "errorResponse" src/app/api/ | wc -l
   ```

2. **Identify violations**:
   ```bash
   # Find handlers with manual error handling (not using errorResponse)
   grep -r "JSON.stringify({.*error" src/app/api/
   grep -r "status:" src/app/api/ | grep -v errorResponse
   ```

3. **Verify errorResponse helper implementation**:
   - Read `src/lib/next/route-helpers.ts` completely
   - Confirm it handles: status codes, error messages, headers
   - Check if it properly uses Context7 schemas for error types

4. **List all affected handlers** (files containing direct NextResponse.json with error):
   - Search with: `grep -l "NextResponse.json" src/app/api/**/route.ts`
   - For each, check line numbers with inline error logic

## Implementation Phase

### Step 1: Audit the helper (read-only)
Open `src/lib/next/route-helpers.ts` and confirm the signature:
- Ensure `errorResponse(status, message, options?)` exists
- Verify it returns `NextResponse` with proper headers
- Check if it integrates with telemetry (`withTelemetrySpan`)

### Step 2: Update each handler (fix violations)
For each file with manual error handling:

**Before**:
```typescript
export async function POST(request: NextRequest) {
  try {
    // ... handler logic
  } catch (error) {
    return NextResponse.json(
      { error: "Internal Server Error", code: "INTERNAL_ERROR" },
      { status: 500 }
    )
  }
}
```

**After**:
```typescript
export async function POST(request: NextRequest) {
  try {
    // ... handler logic
  } catch (error) {
    return errorResponse(500, "Internal Server Error", { code: "INTERNAL_ERROR" })
  }
}
```

### Step 3: Search and replace pattern
Use your editor to find all handlers that don't use `errorResponse`:
1. Ensure `errorResponse` is imported: `import { errorResponse } from '@/lib/next/route-helpers'`
2. Replace manual `NextResponse.json({ error })` calls with `errorResponse(status, msg, opts)`
3. Verify consistent error code values (use `@schemas/error-codes` if it exists)

### Step 4: Standardize error codes
Check if all errors use consistent codes from a single source:
- If `@schemas/error-codes.ts` exists, reference it
- Otherwise, create a comment documenting expected codes
- Ensure 400-class errors vs 500-class errors are correctly classified

## Verification Phase

### Test: Type checking
```bash
pnpm type-check
```
Must pass with no errors.

### Test: Linting
```bash
pnpm biome:check src/app/api/
```
Verify all handlers pass Biome checks.

### Test: Build
```bash
pnpm build
```
Ensure no build errors in API routes.

### Test: Smoke test (if E2E exists)
```bash
pnpm test:api
```
If endpoint tests exist, verify they still pass.

## Rollback

If needed, revert with:
```bash
git diff src/app/api/ # review changes
git checkout src/app/api/ # undo all changes
```

---

## Acceptance Criteria

- [ ] All `src/app/api/**/route.ts` files use `errorResponse()` for errors
- [ ] No manual `NextResponse.json({ error })` in API handlers
- [ ] Type checking passes
- [ ] Biome formatting passes
- [ ] Build succeeds
- [ ] Error codes are consistent and documented
```

---

## Prompt 2: Extract Repeated Zod Schema Patterns into Reusable Validators

**Task ID**: IMPL-002
**Category**: Code Duplication & Library Leverage
**Severity**: HIGH
**Effort**: Medium
**Scope**: `src/domain/schemas/*.ts` (5-8 files, ~100 lines total changes)

**Dependencies**: None

---

```markdown
# Extract Repeated Zod Schema Patterns into Reusable Validators

## Problem

Zod schemas across `@schemas/*` repeat similar validation patterns:
- Multiple schemas with `z.string().email()` validation with identical error messages
- Similar UUID/ID validation patterns duplicated in different files
- Date range validation patterns (start/end dates with relative constraints) appear multiple times
- Common field combinations (e.g., pagination: limit, offset) defined separately in each domain

AGENTS.md 4.4 & 4.5 require: "Schema organization in single files per domain with reusable patterns."

## Investigation Phase

1. **Find repeated patterns**:
   ```bash
   grep -r "z.string().email()" src/domain/schemas/
   grep -r "z.string().uuid()" src/domain/schemas/
   grep -r "start.*z.number()" src/domain/schemas/
   grep -r "limit.*offset" src/domain/schemas/
   ```

2. **Audit each schema file**:
   - Read `src/domain/schemas/*.ts` (all of them)
   - Document identical validation patterns
   - Note which domains define pagination, filtering, date ranges

3. **Create a patterns inventory**:
   - List: email validation, UUID validation, date range (start > end check), pagination, status enums
   - For each, count occurrences and list file locations

## Implementation Phase

### Step 1: Create a shared validators file
**New file**: `src/domain/schemas/validators.ts`

```typescript
/**
 * Reusable Zod validator patterns to avoid duplication across domains.
 * Import these rather than redefining inline.
 */
import { z } from 'zod'

// ===== EMAIL VALIDATION =====
export const emailValidator = z.string().email({
  error: 'Must be a valid email address',
})

// ===== ID / UUID VALIDATION =====
export const uuidValidator = z.string().uuid({
  error: 'Must be a valid UUID',
})

export const idValidator = z.string().min(1, {
  error: 'ID cannot be empty',
})

// ===== DATE VALIDATION =====
export const isoDateValidator = z.string().datetime({
  error: 'Must be a valid ISO 8601 date',
})

// ===== PAGINATION SCHEMA =====
export const paginationSchema = z.object({
  limit: z.number().int().positive({ error: 'Limit must be positive' }).default(20),
  offset: z.number().int().nonnegative({ error: 'Offset must be non-negative' }).default(0),
})

export type Pagination = z.infer<typeof paginationSchema>

// ===== DATE RANGE SCHEMA =====
export const dateRangeSchema = z.object({
  startDate: isoDateValidator,
  endDate: isoDateValidator,
}).refine(
  (data) => new Date(data.startDate) <= new Date(data.endDate),
  { message: 'Start date must be before end date', path: ['endDate'] }
)

export type DateRange = z.infer<typeof dateRangeSchema>

// Add more as discovered...
```

### Step 2: Migrate existing schemas
For each file in `src/domain/schemas/`:
1. Open and identify duplicated patterns
2. Replace inline definitions with imports from `validators.ts`
3. Ensure all imports are updated correctly

**Before** (e.g., in `calendar.ts`):
```typescript
export const EventSchema = z.object({
  email: z.string().email({ error: 'Must be a valid email address' }),
  startTime: z.string().datetime({ error: 'Must be a valid ISO 8601 date' }),
  endTime: z.string().datetime({ error: 'Must be a valid ISO 8601 date' }),
})
```

**After**:
```typescript
import { emailValidator, isoDateValidator, dateRangeSchema } from './validators'

export const EventSchema = z.object({
  email: emailValidator,
  startTime: isoDateValidator,
  endTime: isoDateValidator,
}).merge(dateRangeSchema)
```

### Step 3: Verify Zod v4 compliance
- Ensure all error messages use the `{ error: 'msg' }` format (v4 only)
- Verify no deprecated `message`, `invalid_type_error`, `required_error` keys
- Check `.refine()` uses correct v4 syntax with `path` field for cross-field validation

### Step 4: Update tests
If schema tests exist in `src/**/__tests__`:
- Update import paths if they referenced schemas
- Ensure tests still cover validator behavior
- Add tests for `validators.ts` if new patterns are added

## Verification Phase

### Test: Type checking
```bash
pnpm type-check
```
All schema imports must resolve correctly.

### Test: Schema validation (unit)
```bash
pnpm test:schemas
```
All schema tests must pass (if they exist).

### Test: Linting
```bash
pnpm biome:check src/domain/schemas/
```

### Test: Build
```bash
pnpm build
```

## Rollback

```bash
git checkout src/domain/schemas/
```

---

## Acceptance Criteria

- [ ] Created `src/domain/schemas/validators.ts` with reusable patterns
- [ ] All duplicated patterns removed from domain-specific files
- [ ] Imports updated to use validators.ts
- [ ] Type checking passes
- [ ] All tests pass (schemas + components using schemas)
- [ ] No `message`, `invalid_type_error`, `required_error` (Zod v3 patterns) remain
```

---

## Prompt 3: Consolidate React Component Form Wrappers

**Task ID**: IMPL-003
**Category**: Code Duplication & Anti-patterns
**Severity**: MEDIUM
**Effort**: Medium
**Scope**: `src/components/**/*form*.tsx` and `src/components/**/*modal*.tsx` (8-12 files, ~150 lines)

**Dependencies**: None

---

```markdown
# Consolidate React Component Form Wrappers into Composable Patterns

## Problem

Form-based components are defined with similar wrapper patterns:
- Modal forms with form + action button combinations are defined separately in multiple places
- Search filters have duplicated layout patterns (container, field section, button group)
- Form header/footer patterns appear in multiple components
- Dialog/modal frame logic duplicates between components

AGENTS.md 4.2 requires: "No unnecessary abstractions. One-time operations should not get helpers."

However, when patterns appear 3+ times identically, extraction is justified.

## Investigation Phase

1. **Find form component patterns**:
   ```bash
   find src/components -name "*form*.tsx" -o -name "*modal*.tsx" | head -20
   ```

2. **Audit structure**:
   - Read each form/modal component
   - Identify the repeating pattern (container > field section > button group)
   - Check prop structure (are they similar?)

3. **Count occurrences**:
   - How many components use "form inside a dialog"?
   - How many implement "search filter form"?
   - How many have "header + scrollable content + footer buttons"?

## Implementation Phase

### Step 1: Identify the pattern to consolidate

Look for patterns like:
```typescript
// Pattern: Dialog + Form + Submit button
<Dialog open={isOpen} onOpenChange={setIsOpen}>
  <DialogContent>
    <DialogHeader>Title</DialogHeader>
    <form onSubmit={...}>
      <FormField ... />
      <FormField ... />
      <DialogFooter>
        <Button>Cancel</Button>
        <Button type="submit">Save</Button>
      </DialogFooter>
    </form>
  </DialogContent>
</Dialog>
```

### Step 2: Extract as a new component

**New file**: `src/components/patterns/form-dialog.tsx`

```typescript
'use client'

import { ReactNode } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

interface FormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  children: ReactNode // Form content
  onSubmit?: () => void | Promise<void>
  isLoading?: boolean
  cancelLabel?: string
  submitLabel?: string
}

export function FormDialog({
  open,
  onOpenChange,
  title,
  children,
  onSubmit,
  isLoading = false,
  cancelLabel = 'Cancel',
  submitLabel = 'Save',
}: FormDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>{title}</DialogHeader>
        {children}
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
          >
            {cancelLabel}
          </Button>
          <Button onClick={onSubmit} disabled={isLoading}>
            {submitLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

### Step 3: Migrate existing components
For each component using the pattern:

**Before**:
```typescript
export function EditUserModal({ isOpen, onClose, user }) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>Edit User</DialogHeader>
        <form>
          <FormField ... />
        </form>
        <DialogFooter>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit">Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

**After**:
```typescript
import { FormDialog } from '@/components/patterns/form-dialog'

export function EditUserModal({ isOpen, onClose, user }) {
  return (
    <FormDialog
      open={isOpen}
      onOpenChange={onClose}
      title="Edit User"
      onSubmit={() => { /* handle submit */ }}
    >
      <form>
        <FormField ... />
      </form>
    </FormDialog>
  )
}
```

### Step 4: Apply to all identified instances
- Update 3+ components that share the pattern
- Verify props are compatible
- Test each updated component

## Verification Phase

### Test: Component render
```bash
pnpm test:components
```
All form/modal components must render without errors.

### Test: Type checking
```bash
pnpm type-check
```

### Test: Biome
```bash
pnpm biome:check src/components/
```

### Test: Manual visual (if applicable)
- Open a component that uses FormDialog
- Verify dialog appears and buttons work
- Verify form content renders

## Rollback

```bash
git checkout src/components/
```

---

## Acceptance Criteria

- [ ] Created reusable pattern component(s) in `src/components/patterns/`
- [ ] Consolidated 3+ instances of repeating pattern
- [ ] Remaining components use new pattern
- [ ] Type checking passes
- [ ] Tests pass
- [ ] No over-abstraction (pattern appears 3+ times, not 1-2)
```

---

## Prompt 4: Remove Dead Code and Obsolete AI-Generated Boilerplate

**Task ID**: IMPL-004
**Category**: Technical Debt & Obsolete Code
**Severity**: MEDIUM
**Effort**: Medium
**Scope**: Various files (20-30 files, ~300 lines removed)

**Dependencies**: None

---

```markdown
# Remove Dead Code and Obsolete AI-Generated Boilerplate

## Problem

The repository contains:
- Unused utility functions never called from anywhere
- Test files for deleted features
- Superseded ADR implementations still present (e.g., old websocket code after migration to HTTP)
- AI-generated boilerplate with overly verbose comments and repeated variable names
- Disabled code blocks marked with `/* commented out */` for months
- Utility files with only 1-2 functions actually used

AGENTS.md 2.2 requires: "Remove superseded legacy code paths immediately after new behavior lands."

## Investigation Phase

1. **Find unused exports**:
   ```bash
   # Using TypeScript compiler to find unused exports
   pnpm type-check --noEmit
   ```

2. **Find unused imports**:
   ```bash
   grep -r "^import.*from" src/ | grep -v test | head -30
   # Manually check if each import is actually used
   ```

3. **Find commented code**:
   ```bash
   grep -r "^[[:space:]]*\/\/" src/ | grep -E "(removed|old|deprecated|fixme|todo)" | head -20
   ```

4. **Find orphaned test files**:
   ```bash
   find src -name "*.test.ts" -o -name "*.spec.ts" | while read f; do
     base=$(echo "$f" | sed 's/\.test\./\./g' | sed 's/\.spec\./\./g')
     [ ! -f "$base" ] && echo "Orphaned: $f"
   done
   ```

5. **Find superseded patterns**:
   - Read ADRs in `docs/architecture/decisions/`
   - For ADRs marked superseded, search for old patterns in code
   - Example: If ADR-0014 replaced old auth, search for old auth helpers

## Implementation Phase

### Step 1: Create an inventory

Build a list of candidates:
- [ ] Unused functions in `src/lib/**`
- [ ] Orphaned test files
- [ ] Commented-out code blocks
- [ ] Superseded implementations (cross-check ADRs)
- [ ] Overly verbose AI-generated functions

### Step 2: Delete unused utilities

For each utility in `src/lib/**` that is unused:
```bash
# Search for usage
grep -r "functionName" src --include="*.ts" --include="*.tsx"
```

If **zero results** (except the definition), delete:
1. The function from the file
2. The export from any barrel files
3. The import from test files (if it exists)

### Step 3: Delete orphaned tests

For test files where the source file has been deleted:
```bash
rm src/path/to/deleted-feature.test.ts
```

### Step 4: Remove commented code

For any commented-out code block older than 3 months (check git blame):
```bash
# Example: find a commented block and delete it
# Before:
// export const oldFunction = () => {
//   return "this was replaced in commit xyz"
// }

# After: (line removed entirely)
```

### Step 5: Refactor AI-generated boilerplate

Common AI patterns to simplify:

**Before** (overly verbose):
```typescript
// Helper function to handle and process user data objects
// This function takes user data and processes it for use in the application
// It accepts a user object and returns a processed user object
function processUserData(user: User): ProcessedUser {
  // Extract the user's name
  const userFullName = user.firstName + ' ' + user.lastName
  // Create the processed user object
  const processedUserObj: ProcessedUser = {
    name: userFullName,
    email: user.email,
  }
  // Return the processed user
  return processedUserObj
}
```

**After** (concise):
```typescript
function processUserData(user: User): ProcessedUser {
  return {
    name: `${user.firstName} ${user.lastName}`,
    email: user.email,
  }
}
```

### Step 6: Consolidate similar utility functions

If two functions do nearly the same thing:
- Keep one with more general parameters
- Update all callers to use the single version
- Delete the duplicate

## Verification Phase

### Test: Build
```bash
pnpm build
```
Must succeed without build errors.

### Test: Type checking
```bash
pnpm type-check
```
No errors.

### Test: Tests
```bash
pnpm test
```
All remaining tests must pass.

### Manual verification
- Spot-check a few files you modified
- Ensure logic is still correct after simplification

## Rollback

```bash
git checkout <files>
```

---

## Acceptance Criteria

- [ ] Removed all unused utility functions
- [ ] Deleted orphaned test files
- [ ] Removed all commented-out code older than 3 months
- [ ] Simplified AI-generated boilerplate
- [ ] Build succeeds
- [ ] All tests pass
- [ ] No regressions in functionality
```

---

## Prompt 5: Standardize AI SDK v6 Usage Across Route Handlers

**Task ID**: IMPL-005
**Category**: Library Leverage & Compliance
**Severity**: HIGH
**Effort**: Medium
**Scope**: `src/app/api/**/route.ts` (10-15 files, ~200 lines)

**Dependencies**: None; Recommend running after IMPL-001 (error handling)

---

```markdown
# Standardize AI SDK v6 Usage Across All Route Handlers

## Problem

Route handlers use AI SDK v6 inconsistently:
- Some use `streamText()` incorrectly without `convertToModelMessages()`
- Some manually construct tool definitions instead of using type-safe schemas
- Some don't properly use `result.toUIMessageStreamResponse()`
- Structured output handlers use `generateObject` but not with standardized schema patterns
- Missing proper OpenTelemetry spans or logger context

AGENTS.md 5.2-5.3 require: "Use AI SDK v6 primitives only. Chat/streaming: `convertToModelMessages()` → `streamText(tools, outputs)` → `result.toUIMessageStreamResponse()`"

## Investigation Phase

1. **Find all AI SDK usage**:
   ```bash
   grep -r "streamText\|generateObject\|generateText\|streamObject" src/app/api --include="*.ts"
   ```

2. **Audit each handler**:
   - Check if using `convertToModelMessages()`
   - Verify tools are properly typed (not inline objects)
   - Check if streaming handlers use `toUIMessageStreamResponse()`
   - Verify structured outputs use Zod schemas from `@schemas/*`

3. **Check for telemetry**:
   ```bash
   grep -r "withTelemetrySpan\|createServerLogger" src/app/api --include="*.ts"
   ```

## Implementation Phase

### Step 1: Audit AI SDK import patterns

**Expected pattern**:
```typescript
import { streamText, generateObject, convertToModelMessages } from 'ai'
import { z } from 'zod'
import { createServerLogger } from '@/lib/telemetry/logger'
import { withTelemetrySpan } from '@/lib/telemetry/span'
```

### Step 2: Standardize chat/streaming handlers

**Before** (incorrect):
```typescript
export async function POST(request: NextRequest) {
  const { messages } = await request.json()

  const result = await streamText({
    model: modelInstance,
    messages: messages, // ❌ Not converted
    tools: {
      search: { // ❌ Inline tool definition
        description: "Search",
        parameters: { type: "object", properties: { q: { type: "string" } } }
      }
    }
  })

  return result.toUIMessageStreamResponse() // ✓ Correct
}
```

**After** (correct):
```typescript
import { convertToModelMessages } from 'ai'
import { searchTool } from '@/ai/tools/search' // Tool schemas in @/ai/tools/*

export async function POST(request: NextRequest) {
  const { messages } = await request.json()
  const logger = createServerLogger('chat-handler')

  return withTelemetrySpan('chat-stream', async () => {
    const result = await streamText({
      model: modelInstance,
      messages: convertToModelMessages(messages), // ✓ Converted
      tools: { search: searchTool }, // ✓ Imported from tools
    })

    logger.info('Chat streamed successfully')
    return result.toUIMessageStreamResponse()
  })
}
```

### Step 3: Standardize structured output handlers

**Before** (missing schema validation):
```typescript
const result = await generateObject({
  model: modelInstance,
  prompt: userInput,
  schema: z.object({ // ❌ Inline schema
    result: z.string(),
  }),
})
```

**After** (proper pattern):
```typescript
import { SearchResultSchema } from '@schemas/search'

const result = await generateObject({
  model: modelInstance,
  prompt: userInput,
  schema: SearchResultSchema, // ✓ From @schemas/*
})
```

### Step 4: Apply to all handlers

For each handler in `src/app/api/**/route.ts`:
1. Ensure proper imports
2. Use `convertToModelMessages()` for all chat messages
3. Import tools from `@/ai/tools/*` (don't define inline)
4. Use `@schemas/*` for structured outputs
5. Wrap with `withTelemetrySpan()` for observability
6. Use `createServerLogger()` for context-aware logging

## Verification Phase

### Test: Build
```bash
pnpm build
```

### Test: Type checking
```bash
pnpm type-check
```
AI SDK types must resolve correctly.

### Test: API tests
```bash
pnpm test:api
```
All handler tests must pass.

### Test: Manual verification
- Make a request to an updated endpoint
- Verify response structure matches expectations
- Check logs for telemetry events

## Rollback

```bash
git diff src/app/api/ # Review
git checkout src/app/api/
```

---

## Acceptance Criteria

- [ ] All chat handlers use `convertToModelMessages()`
- [ ] All handlers use `streamText()` or `generateObject()` (not custom implementations)
- [ ] All tools defined in `@/ai/tools/*` (not inline)
- [ ] All structured outputs use schemas from `@schemas/*`
- [ ] All handlers wrapped with `withTelemetrySpan()`
- [ ] Build passes
- [ ] API tests pass
- [ ] Type checking passes
```

---

## Prompt 6: Optimize Zustand Store Middleware Ordering and Computed Properties

**Task ID**: IMPL-006
**Category**: Library Leverage & Best Practices
**Severity**: MEDIUM
**Effort**: Small-Medium
**Scope**: `src/stores/**` (5-10 files, ~100 lines)

**Dependencies**: None

---

```markdown
# Optimize Zustand Store Middleware Ordering and Computed Properties

## Problem

Zustand stores may have:
- Incorrect middleware ordering (should be: `devtools` → `persist` → `withComputed` → store)
- Computed properties doing unnecessary work (non-O(1) calculations on every selector call)
- Simple accessors implemented as computed properties instead of selectors
- Missing memoization on expensive selectors

AGENTS.md 4.3 requires: "Middleware order: `devtools` → `persist` → `withComputed` → store creator. Computed properties innermost. Keep compute functions O(1) or O(n). Never use for simple access (use selectors), async ops, or React context-dependent values."

## Investigation Phase

1. **Find all Zustand stores**:
   ```bash
   find src/stores -name "*.ts" | grep -v "__tests__"
   ```

2. **Audit middleware order**:
   - Open each store file
   - Check the middleware application order
   - Verify `withComputed` is last/innermost

3. **Audit computed properties**:
   - Check each computed property
   - Verify it's O(1) or O(n)
   - Ensure it's not a simple accessor (use selector instead)
   - Confirm it's not async (those should be actions)

## Implementation Phase

### Step 1: Fix middleware ordering

**Before** (incorrect):
```typescript
export const useSearchStore = create<SearchState>()(
  withComputed<SearchState>(
    persist(
      devtools((set) => ({ /* state */ })),
      { name: 'search' }
    ),
    {
      isLoading: (state) => state.loading,
    }
  )
)
```

**After** (correct):
```typescript
export const useSearchStore = create<SearchState>()(
  devtools(
    persist(
      withComputed<SearchState>(
        (set) => ({ /* state */ }),
        {
          isLoading: (state) => state.loading,
        }
      ),
      { name: 'search' }
    )
  )
)
```

### Step 2: Migrate simple accessors to selectors

**Before** (using computed property):
```typescript
const store = withComputed(creator, {
  currentUser: (state) => state.user,
  hasAuth: (state) => state.token !== null,
})

// Usage:
const currentUser = store.getState().currentUser
```

**After** (using selectors):
```typescript
export const useCurrentUser = () => useStore((s) => s.user)
export const useHasAuth = () => useStore((s) => s.token !== null)

// Usage:
const currentUser = useCurrentUser()
```

### Step 3: Optimize expensive computed properties

Only keep computed properties for:
- O(1) operations (single field access, boolean checks)
- O(n) operations that are truly valuable (e.g., sum of items, filtered list that's used everywhere)

**Example kept**:
```typescript
withComputed(creator, {
  totalCount: (state) => state.items.length, // O(1)
  filteredItems: (state) =>
    state.items.filter((i) => i.status === state.filterStatus), // O(n), used everywhere
})
```

**Example removed** (use selector instead):
```typescript
// Before: computed property
withComputed(creator, {
  isLoading: (state) => state.status === 'loading', // Simple - use selector
})

// After: selector
export const useIsLoading = () => useStore((s) => s.status === 'loading')
```

### Step 4: Add logger integration

Ensure store has proper error tracking:
```typescript
import { createStoreLogger } from '@/lib/telemetry/store-logger'

export const useStore = create<State>()(
  devtools(
    persist(
      withComputed(creator, { /* computed */ }),
      { name: 'store-name' }
    ),
    {
      // Enable store logger for error tracking
      enabled: process.env.NODE_ENV === 'development',
    }
  ),
  // Apply store logger
  createStoreLogger<State>('store-name')
)
```

## Verification Phase

### Test: Type checking
```bash
pnpm type-check
```

### Test: Component tests
```bash
pnpm test:components
```
Components using stores must render and work correctly.

### Test: Store unit tests
```bash
pnpm test src/stores
```
If tests exist, verify they pass.

### Manual verification
- Open a component that uses the store
- Verify selectors work correctly
- Check browser console for store updates

## Rollback

```bash
git checkout src/stores/
```

---

## Acceptance Criteria

- [ ] All stores use middleware order: `devtools` → `persist` → `withComputed`
- [ ] Computed properties are O(1) or O(n) only
- [ ] Simple accessors migrated to selectors
- [ ] Async operations in actions (not computed)
- [ ] Store logger integrated
- [ ] Type checking passes
- [ ] All tests pass
```

---

## Prompt 7: Consolidate MSW Handlers and Remove Test Setup Duplication

**Task ID**: IMPL-007
**Category**: Code Duplication & Testing
**Severity**: MEDIUM
**Effort**: Small
**Scope**: `src/test/**` (3-5 files, ~100 lines)

**Dependencies**: None

---

```markdown
# Consolidate MSW Handlers and Test Setup Duplication

## Problem

Test files have duplicated:
- Mock setup patterns across multiple test files
- MSW handler definitions (handlers defined in test files instead of centralized)
- Server reset logic called in multiple beforeEach blocks
- Environment variable mocking repeated across tests

AGENTS.md 6.1 requires: "MSW-first: Network mocking via MSW only; handlers in `src/test/msw/handlers/*`."

## Investigation Phase

1. **Find duplicated test setup**:
   ```bash
   grep -r "beforeEach" src/**/__tests__ | head -20
   grep -r "MSW\|setupServer\|server.listen" src/**/__tests__
   ```

2. **Find inline MSW handlers**:
   ```bash
   grep -r "http.get\|http.post" src/**/__tests__
   ```

3. **Audit MSW centralization**:
   - Check if `src/test/msw/handlers/*` exists and is used
   - Verify all handlers are defined there (not inline in tests)
   - Confirm server setup is centralized in `src/test/msw/server.ts`

## Implementation Phase

### Step 1: Centralize MSW handlers

**Expected structure**:
```
src/test/msw/
  handlers/
    auth.ts        # All auth endpoints
    search.ts      # All search endpoints
    calendar.ts    # All calendar endpoints
    index.ts       # Export all handlers
  server.ts        # Centralized server setup
  setup.ts         # Test environment setup
```

### Step 2: Move handlers from test files to centralized location

**Before** (in test file):
```typescript
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

const server = setupServer(
  http.get('/api/search', () => HttpResponse.json({ results: [] }))
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

test('search returns results', async () => { /* ... */ })
```

**After** (handler in `src/test/msw/handlers/search.ts`):
```typescript
import { http, HttpResponse } from 'msw'

export const searchHandlers = [
  http.get('/api/search', () => HttpResponse.json({ results: [] })),
]
```

**After** (in test file):
```typescript
import { server } from '@/test/msw/server'

beforeEach(() => server.resetHandlers())

test('search returns results', async () => { /* ... */ })
```

### Step 3: Consolidate test setup

Create or update `src/test/msw/setup.ts`:
```typescript
import { beforeAll, afterAll, afterEach } from 'vitest'
import { server } from './server'

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

Then in each test file:
```typescript
// First line
import '@/test/msw/setup'
```

### Step 4: Consolidate environment mocking

Create `src/test/utils/setup-env.ts`:
```typescript
export function setupTestEnv(env: Record<string, string> = {}) {
  const originalEnv = { ...process.env }

  Object.assign(process.env, {
    NEXT_PUBLIC_API_URL: 'http://localhost:3000',
    ...env,
  })

  return () => {
    Object.assign(process.env, originalEnv)
  }
}
```

**Before** (in test):
```typescript
beforeEach(() => {
  process.env.NEXT_PUBLIC_API_URL = 'http://localhost:3000'
})
```

**After**:
```typescript
import { setupTestEnv } from '@/test/utils/setup-env'

const cleanup = setupTestEnv()
afterEach(cleanup)
```

## Verification Phase

### Test: All tests
```bash
pnpm test
```
All tests must pass with centralized setup.

### Test: Coverage
```bash
pnpm test --coverage
```
Verify coverage doesn't drop after consolidation.

## Rollback

```bash
git checkout src/test/
```

---

## Acceptance Criteria

- [ ] All MSW handlers moved to `src/test/msw/handlers/`
- [ ] Centralized server setup in `src/test/msw/server.ts`
- [ ] Centralized environment setup in `src/test/utils/setup-env.ts`
- [ ] No inline MSW handler definitions in test files
- [ ] All tests pass
- [ ] Coverage maintained
```

---

## Prompt 8: Remove Type `any` and Unsafe Casts from Production Code

**Task ID**: IMPL-008
**Category**: Code Quality & Type Safety
**Severity**: HIGH
**Effort**: Medium
**Scope**: `src/**/*.ts(x)` excluding tests (varies by findings, ~50-100 lines)

**Dependencies**: None

---

```markdown
# Remove Type `any` and Unsafe Casts from Production Code

## Problem

Production code may contain:
- `any` type annotations (violates strict mode)
- `as unknown as T` casts outside test code (violates AGENTS.md 4.2)
- Untyped function parameters or return values
- Over-broad `object` or `unknown` types that could be specific

AGENTS.md 4.2 requires: "Avoid `any`. Use precise unions/generics. Unsafe casts (`as unknown as T`) forbidden in production code (CI runs `pnpm check:no-new-unknown-casts`)."

## Investigation Phase

1. **Find `any` usages**:
   ```bash
   grep -r ": any\|as any" src --include="*.ts" --include="*.tsx" | grep -v __tests__
   ```

2. **Find unsafe casts**:
   ```bash
   grep -r "as unknown as" src --include="*.ts" --include="*.tsx" | grep -v __tests__
   ```

3. **Find untyped parameters/returns**:
   ```bash
   grep -r "function.*)\|const.*=.*(" src --include="*.ts" | grep -v ": " | head -20
   ```

## Implementation Phase

### Step 1: Fix `any` types

**Before**:
```typescript
function processData(data: any) {
  return data.value
}
```

**After** (with proper type):
```typescript
interface DataObject {
  value: string
}

function processData(data: DataObject) {
  return data.value
}
```

**Or** (if truly dynamic):
```typescript
function processData(data: unknown) {
  if (typeof data === 'object' && data !== null && 'value' in data) {
    return (data as { value: string }).value
  }
  throw new Error('Invalid data')
}
```

### Step 2: Replace unsafe casts with type guards

**Before**:
```typescript
const config = JSON.parse(configStr) as unknown as Config
```

**After** (with validation):
```typescript
import { configSchema } from '@schemas/config'

const configData = JSON.parse(configStr)
const config = configSchema.parse(configData) // Throws if invalid
```

### Step 3: Fix untyped function signatures

**Before**:
```typescript
const handleSubmit = (e) => {
  e.preventDefault()
}
```

**After**:
```typescript
const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
  e.preventDefault()
}
```

### Step 4: Run the safety check

```bash
pnpm check:no-new-unknown-casts
```

This must pass with zero violations in production code.

## Verification Phase

### Test: Type checking
```bash
pnpm type-check
```
Must pass with strict mode.

### Test: Build
```bash
pnpm build
```

### Test: Safety check
```bash
pnpm check:no-new-unknown-casts
```

## Rollback

```bash
git checkout src/
```

---

## Acceptance Criteria

- [ ] No `any` types in production code
- [ ] No `as unknown as T` casts in production code (test code can use `unsafeCast<T>()`)
- [ ] All function parameters and returns properly typed
- [ ] Type checking passes with strict mode
- [ ] `pnpm check:no-new-unknown-casts` passes
- [ ] Build succeeds
```

---

## Prompt 9: Organize API Routes by Resource/Feature Pattern

**Task ID**: IMPL-009
**Category**: Directory Structure & Organization
**Severity**: LOW-MEDIUM
**Effort**: Medium
**Scope**: `src/app/api/` (reorganization, no code changes)

**Dependencies**: None; Safe to defer

---

```markdown
# Organize API Routes by Resource/Feature Pattern

## Problem

API routes may be organized inconsistently:
- Some endpoints grouped by action (all GET routes, then all POST)
- Some grouped by domain (all calendar, all search)
- Mixed naming: `/api/v1/users` vs `/api/users/` vs `/api/user`
- Unclear which routes are public vs authenticated vs admin

AGENTS.md 3 section "Primary app" and 5.1 require clarity on route structure and adherence to REST patterns.

## Investigation Phase

1. **Map current structure**:
   ```bash
   find src/app/api -type f -name "route.ts" | sort
   ```

2. **Document route organization**:
   - Group routes by domain (auth, calendar, search, etc.)
   - Note naming inconsistencies
   - Identify unclear resource vs action routes

3. **Check ADRs** for guidance:
   - ADR-0029 (DI Route Handlers)
   - ADR-0031 (Next.js Chat API)
   - Route exceptions in `docs/architecture/route-exceptions.md`

## Implementation Phase

### Step 1: Decide on organization principle

**Principle**: Organize by **resource**, with clear hierarchy:
```
src/app/api/
  auth/
    route.ts           # POST /api/auth (login)
    logout/route.ts    # POST /api/auth/logout
    refresh/route.ts   # POST /api/auth/refresh
  users/
    route.ts           # GET/POST /api/users
    [id]/
      route.ts         # GET/PUT/DELETE /api/users/:id
  calendar/
    [id]/
      events/
        route.ts       # GET /api/calendar/:id/events
  search/
    route.ts           # POST /api/search (general search)
    flights/route.ts   # POST /api/search/flights (specialized)
```

### Step 2: Migrate routes if needed

For each route that's misplaced:
1. Create target directory structure
2. Move `route.ts` file
3. Update imports in the handler
4. Verify route paths match directory structure

### Step 3: Standardize naming

- Use **plural** resource names: `/users`, not `/user`
- Use **lowercase**: `/api/calendar`, not `/api/Calendar`
- Use **hyphens** for multi-word: `/api/upcoming-flights`, not `/api/upcomingFlights`

### Step 4: Add middleware guard (optional)

If not already present, consider adding route-level auth guards:
```typescript
// src/app/api/middleware.ts
export const config = {
  matcher: ['/api/((?!auth).*)'],
}

export function middleware(request: NextRequest) {
  const token = request.headers.get('authorization')
  if (!token) {
    return errorResponse(401, 'Unauthorized')
  }
}
```

## Verification Phase

### Test: Build
```bash
pnpm build
```
Routes must be discoverable.

### Test: Type checking
```bash
pnpm type-check
```

### Manual verification
- Verify each route is accessible at its new path
- Test requests to moved endpoints
- Confirm old paths are no longer served

## Rollback

```bash
git checkout src/app/api/
```

---

## Acceptance Criteria

- [ ] Routes organized by resource (clear hierarchy)
- [ ] Consistent naming (plural, lowercase, hyphens)
- [ ] All routes are discoverable and type-safe
- [ ] Build passes
- [ ] Documentation updated if endpoints listed elsewhere
- [ ] No broken routes
```

---

## Final Notes for All Prompts

**Before running any prompt**:
1. Ensure you're on a clean git branch
2. Run `pnpm install` to ensure dependencies are current
3. Run `pnpm type-check` as a baseline

**After completing each prompt**:
1. Run all verification steps (type-check, biome, tests)
2. Review git diff for unexpected changes
3. Commit with conventional commit message (feat/fix/refactor scope: description)

**If a prompt fails**:
- Read the error message carefully
- Verify file paths are correct (file may have been moved)
- Check if another prompt needs to run first (see Dependencies)
- Ask for clarification on the specific failure

**Combining multiple prompts**:
- Prompts are independent and can run in any order
- If combining, run IMPL-001 (error handling) first for consistency
- Then run IMPL-002, IMPL-004, IMPL-005 in any order
- Run IMPL-003, IMPL-006, IMPL-007, IMPL-008 after foundational changes

---

END OF IMPLEMENTATION PROMPTS
```
