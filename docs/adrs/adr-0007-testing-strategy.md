# ADR-0007: Modern Testing Strategy with Vitest and Playwright

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-06-17
**Category**: ops
**Domain**: Testing (Vitest/Playwright)

## Context

TripSage requires a testing strategy that:

- Achieves 80-90% code coverage across frontend and backend
- Supports modern React 19 and Next.js 15 features
- Enables fast test execution for rapid development
- Provides E2E testing for critical user journeys
- Focuses on behavior over implementation details

Our current test suite has significant issues:

- Legacy patterns incompatible with modern React
- Poor coverage (~45% frontend, ~60% backend)
- Slow execution times
- Brittle tests tied to implementation

## Decision

We will adopt a modern testing strategy:

**Frontend Testing Stack:**

- **Unit/Component**: Vitest with browser mode
- **Integration**: React Testing Library
- **E2E**: Playwright
- **Visual Regression**: Playwright screenshots

**API Testing Stack:**

- **Route Handlers**: Vitest with MSW for mocking
- **Integration**: Vitest with real database (test containers)

**Key Principles:**

- Behavior-driven testing (what users see/do)
- Real browser testing for components
- API mocking with MSW
- Parallel test execution

## Consequences

### Positive

- **Speed**: Vitest is significantly faster than Jest
- **Accuracy**: Browser mode tests real browser behavior
- **Maintainability**: Behavior-focused tests are more stable
- **Coverage**: Easier to achieve 90%+ coverage targets
- **DX**: Better error messages and debugging experience
- **Modern**: Full support for React 19 features

### Negative

- **Migration Effort**: Complete test rewrite required
- **Learning Curve**: Team needs to learn new tools
- **Initial Investment**: 2-3 weeks to rewrite test suite
- **Tool Fragmentation**: Different tools for different test types

### Neutral

## Changelog

- 1.0.0 (2025-10-24) — Standardized metadata and formatting; added version and changelog.

- Different configuration and setup patterns
- New test organization structure needed
- Changes to CI/CD pipeline configuration

## Alternatives Considered

### Jest + React Testing Library

Traditional React testing setup.

**Why not chosen**:

- Slower execution, especially with JSDOM
- No native browser testing support
- Configuration complexity with modern tools
- Less suitable for React 19 features

### Cypress

Popular E2E testing framework.

**Why not chosen**:

- Slower than Playwright
- Less flexible architecture
- Separate toolchain from unit tests
- More resource intensive

### Keep Current Tests

Maintain and fix existing test suite.

**Why not chosen**:

- Would require extensive refactoring anyway
- Legacy patterns don't support new features
- Poor ROI on fixing fundamentally flawed tests
- Wouldn't achieve coverage goals

## References

- [Testing Strategy Guide](../04_DEVELOPMENT_GUIDE/TESTING_STRATEGY.md)
- [Modern Test Patterns](../testing/MODERN_TEST_PATTERNS.md)
- [Frontend Implementation Plan - Testing Section](../10_RESEARCH/frontend/comprehensive-implementation-plan-2025.md#phase-2-testing-infrastructure-revolution-weeks-5-6)
- [Vitest Documentation](https://vitest.dev/)
- [Playwright Documentation](https://playwright.dev/)
