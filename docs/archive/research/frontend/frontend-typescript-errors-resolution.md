# Frontend TypeScript Errors Resolution Research

## Executive Summary

This document provides comprehensive research findings on resolving TypeScript compilation errors in the TripSage frontend, specifically addressing React Query v5 compatibility issues, Next.js 15 + React 19 TypeScript errors, and related dependency problems.

## Key Findings

### 1. React Query v5 Breaking Changes

#### Major API Changes

- **Single Object Signature**: All hooks now use a single object parameter instead of multiple overloads
- **Removed Callbacks**: `onSuccess`, `onError`, and `onSettled` have been removed from hook options
- **QueryKey Type Changes**: Query keys must properly type mixed arrays with `(string | Record<string, any>)[]`
- **TypeScript Requirements**: Minimum TypeScript 4.7 required

#### Migration Patterns

1. **Hook Signature Updates**:

   ```typescript
   // Old (v4)
   useQuery(key, fn, options);

   // New (v5)
   useQuery({ queryKey, queryFn, ...options });
   ```

2. **Callback Replacement Pattern**:

   ```typescript
   // Old (v4)
   useQuery({
     queryKey: ["todos"],
     queryFn: fetchTodos,
     onSuccess: (data) => {
       console.log(data);
     },
   });

   // New (v5)
   const query = useQuery({
     queryKey: ["todos"],
     queryFn: fetchTodos,
   });

   useEffect(() => {
     if (query.data) {
       console.log(query.data);
     }
   }, [query.data]);
   ```

3. **QueryKey Type Fix**:

   ```typescript
   // For mixed array types
   type ApiQueryOptions<TData, TError> = Omit<
     UseQueryOptions<TData, TError, TData, (string | Record<string, any>)[]>,
     "queryKey" | "queryFn"
   >;
   ```

### 2. Common TypeScript Compilation Errors

#### Error Categories

1. **Missing Dependencies**: Radix UI packages not installed
2. **Type Conflicts**: Component prop interfaces conflicting with HTML attributes
3. **React 19 Hook Changes**: `useOptimistic` signature changes
4. **Import/Export Issues**: Duplicate exports and missing re-exports
5. **Store Method References**: Incorrect store usage patterns

#### Specific Solutions

1. **Missing Radix UI Packages**:

   ```bash
   pnpm add @radix-ui/react-checkbox @radix-ui/react-dialog @radix-ui/react-dropdown-menu
   ```

2. **Type Conflict Resolution**:

   ```typescript
   // Use Omit to exclude conflicting properties
   interface LoadingSpinnerProps
     extends Omit<React.HTMLAttributes<HTMLDivElement>, "color"> {
     color?: string;
   }
   ```

3. **useOptimistic Hook Update**:

   ```typescript
   // React 19 pattern
   const [optimisticState, setOptimisticState] = useOptimistic(initialState);
   // Then use setOptimisticState separately
   ```

### 3. Next.js 15 + React 19 Considerations

#### Known Issues

- Some Radix UI packages may have peer dependency conflicts with React 19
- TypeScript strict mode reveals more type issues
- React Server Components compatibility concerns

#### Recommended Approaches

1. Use `--legacy-peer-deps` flag when necessary
2. Update all Radix UI packages to latest versions
3. Ensure proper "use client" directives for client components
4. Validate all imports are from correct packages

### 4. Parallel Resolution Strategy

#### Recommended Task Distribution

1. **Task 1: React Query v5 Migration**

   - Update all `useQuery` hooks to object syntax
   - Replace callbacks with `useEffect` patterns
   - Fix queryKey type definitions

2. **Task 2: Dependency Installation**

   - Install all missing Radix UI packages
   - Update package versions for React 19 compatibility
   - Resolve peer dependency conflicts

3. **Task 3: Type Error Fixes**

   - Fix component prop type conflicts
   - Update hook usage patterns
   - Resolve import/export issues

4. **Task 4: Store Integration**
   - Update store method references
   - Fix orchestrator store usage
   - Validate all store connections

## Implementation Plan

### Phase 1: Immediate Fixes (Parallel Execution)

```bash
# Task 1: Install missing dependencies
pnpm add @radix-ui/react-checkbox @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-hover-card @radix-ui/react-menubar @radix-ui/react-scroll-area @radix-ui/react-separator @radix-ui/react-sheet @radix-ui/react-switch @radix-ui/react-tabs @radix-ui/react-tooltip

# Task 2: Update React Query hooks (automated with find/replace)
# Use regex patterns to update hook signatures

# Task 3: Fix type definitions
# Update all mixed array query keys
# Fix component prop interfaces
```

### Phase 2: Testing and Validation

1. Run `pnpm build` after each major fix
2. Use `pnpm tsc --noEmit` for type checking only
3. Run `npx biome check --apply .` for linting

### Phase 3: Final Verification

1. Ensure all TypeScript errors are resolved
2. Run full test suite
3. Verify application functionality

## Best Practices

1. **Type Safety**: Always provide explicit types for query keys and data
2. **Migration Tools**: Use codemods where available
3. **Incremental Updates**: Fix errors in logical groups
4. **Documentation**: Update component documentation with new patterns

## Tools and Resources

1. **React Query v5 Codemod**:

   ```bash
   npx jscodeshift@latest ./src/ \
     --extensions=ts,tsx \
     --parser=tsx \
     --transform=./node_modules/@tanstack/react-query/build/codemods/src/v5/remove-overloads/remove-overloads.cjs
   ```

2. **TypeScript Compiler Options**:

   ```json
   {
     "compilerOptions": {
       "strict": true,
       "skipLibCheck": true,
       "noEmit": true
     }
   }
   ```

3. **Useful Commands**:

   ```bash
   # Type check only
   pnpm tsc --noEmit

   # Find React Query usage
   grep -r "useQuery\|useMutation" src/

   # Check for missing imports
   pnpm ls @radix-ui
   ```

## Conclusion

The majority of TypeScript errors stem from React Query v5 breaking changes and missing Radix UI dependencies. By following the parallel resolution strategy and implementing the fixes systematically, all compilation errors can be resolved efficiently. The key is to address dependency issues first, then tackle type errors in logical groups while maintaining backward compatibility where possible.
