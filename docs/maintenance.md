# Development Maintenance

TripSage development maintenance checklist and procedures.

## Monthly Checks

### Code Quality

- [ ] Run `pnpm biome:check` - ensure no linting errors
- [ ] Run `pnpm type-check` - verify TypeScript compilation
- [ ] Check for unused imports or variables
- [ ] Review recent code changes for patterns

### Testing

- [ ] Run test suite: `pnpm test:run`
- [ ] Check test coverage: `pnpm test:coverage`
- [ ] Review failing tests and fix or document
- [ ] Update test utilities if patterns change

### Dependencies

- [ ] Check for outdated packages: `pnpm outdated`
- [ ] Review security vulnerabilities: `pnpm audit`
- [ ] Update minor versions if compatible
- [ ] Test after dependency updates

## Quarterly Reviews

### Architecture

- [ ] Review factory adoption metrics
- [ ] Check for code duplication patterns
- [ ] Assess store composition effectiveness
- [ ] Evaluate new patterns for consistency

### Performance

- [ ] Benchmark build times
- [ ] Check bundle size trends
- [ ] Review API response times
- [ ] Analyze database query performance

### Documentation

- [ ] Update API documentation for new endpoints
- [ ] Review and update code comments
- [ ] Check documentation links are working
- [ ] Update examples and guides as needed

## Adding New Code

### New API Route

- [ ] Use `withApiGuards` factory
- [ ] Add rate limit config to `ROUTE_RATE_LIMITS`
- [ ] Include telemetry span name
- [ ] Use centralized test helpers
- [ ] No inline auth/rate-limit code
- [ ] Follow REST conventions

### New Store

- [ ] Evaluate if slicing needed (>500 LOC)
- [ ] Use composition helpers from `@/lib/stores`
- [ ] Include devtools middleware
- [ ] Add persistence if state needs to survive reloads
- [ ] Use centralized test helpers from `@/test/store-helpers.ts`
- [ ] Export from appropriate index
- [ ] For chat/memory stores: Use orchestrator hooks for cross-slice coordination

### New Component

- [ ] Use TypeScript with strict types
- [ ] Follow component naming conventions
- [ ] Include proper accessibility attributes
- [ ] Add loading and error states
- [ ] Use centralized test helpers
- [ ] Follow design system patterns

### New AI SDK Integration

- [ ] Implement AI operations in API route handlers, not client slices
- [ ] Use `convertToModelMessages()` for message transformation
- [ ] Use `streamText()`/`generateText()` for completions
- [ ] Return `toUIMessageStreamResponse()` for streaming responses
- [ ] Client-side: Use `@/lib/chat/api-client.ts` for AI API calls
- [ ] Construct `UIMessage` with `parts` array (not `content` property)
- [ ] Parse SSE streams for `text-delta` chunks on client
- [ ] Include proper error handling and abort signal support

### New Test

- [ ] Use centralized utilities from `@/test/*`:
  - `@/test/store-helpers.ts` - Zustand store testing
  - `@/test/factories.ts` - Mock data creation
  - `@/test/api-helpers.ts` - API testing utilities
  - `@/test/schema-helpers.ts` - Zod validation testing
  - `@/test/component-helpers.tsx` - React component testing
- [ ] No `_shared.ts` files in feature directories (all utilities centralized)
- [ ] Include proper setup and teardown with centralized helpers
- [ ] Test behavior, not implementation
- [ ] Maintain >90% coverage target

## Code Review Checklist

### General

- [ ] Code follows established patterns
- [ ] No console.log statements in production code
- [ ] Proper error handling and user feedback
- [ ] Security considerations addressed
- [ ] Performance implications reviewed

### TypeScript Tooling

- [ ] Strict null checks enabled
- [ ] No `any` types without justification
- [ ] Proper generic constraints
- [ ] Interface vs type alias consistency

### React/Frontend

- [ ] Proper key props on lists
- [ ] No unnecessary re-renders
- [ ] Accessibility compliance
- [ ] Responsive design considerations

### API/Backend

- [ ] Input validation implemented
- [ ] Proper HTTP status codes
- [ ] Rate limiting configured
- [ ] Authentication/authorization checked

## Emergency Procedures

### Build Failures

1. Check for TypeScript errors: `pnpm type-check`
2. Verify dependencies: `pnpm install`
3. Check for circular imports
4. Review recent changes for breaking changes

### Test Failures

1. Run tests individually: `pnpm test:run -- --reporter=verbose`
2. Check test environment setup
3. Verify mock configurations
4. Review changes to shared test utilities

### Performance Regressions

1. Compare build times with previous version
2. Check bundle size changes
3. Review database query performance
4. Analyze memory usage patterns

## Tool Updates

### Biome

- Update regularly for new rules
- Review breaking changes before major updates
- Test after updates to ensure no regressions

### TypeScript

- Stay within 1-2 versions of latest
- Review breaking changes in release notes
- Update gradually with proper testing

### Testing Framework

- Keep Vitest and testing-library updated
- Review API changes before updates
- Update test utilities as needed

## Metrics Tracking

### Code Metrics

- Lines of code by component
- Factory adoption percentage
- Test coverage trends
- Bundle size over time

### Quality Metrics

- Build time consistency
- Type check performance
- Test execution time
- Error rates and patterns

Track these metrics quarterly and address trends that indicate code quality degradation.
