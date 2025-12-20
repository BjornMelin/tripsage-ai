# TripSage AI - Comprehensive Repository Analysis Prompt for Gemini-3-Pro

**Context:** Analyze the TripSage AI Next.js 16 + AI SDK v6 application using the optimized packed context below (362K tokens, production code + active standards). Produce a deeply researched, actionable report identifying optimization opportunities across architecture, code quality, dependencies, and build performance.

**Note**: Context excludes superseded ADRs, tests, old implementation guides, and dead code to focus on active codebase.

---

## Analysis Scope & Objectives

### Primary Focus Areas (Priority Order)

1. **Code Duplication & Consolidation (25% focus)**
   - Identify repeated patterns across route handlers, components, and utilities
   - Find similar validation/schema definitions that could be unified
   - Detect component composition patterns that appear multiple times
   - Suggest extraction of common abstractions without over-engineering
   - Focus on genuinely redundant code, not false positives

2. **Dependency Leverage & Library Optimization (20% focus)**
   - Audit current library usage: Are we using `@ai-sdk/*`, `zod`, `zustand`, `react-query` to their full potential?
   - Identify custom code that should use existing libraries instead
   - Find outdated or deprecated patterns (e.g., old AI SDK v5 patterns in v6 context)
   - Spot suboptimal library configurations (e.g., suboptimal middleware ordering in Zustand)
   - Recommend library version or dependency upgrades where appropriate
   - Verify if OpenTelemetry instrumentation is comprehensive or leaving gaps

3. **Technical Debt & Obsolete Code (20% focus)**
   - Identify dead code, unused exports, and orphaned utilities
   - Find outdated ADRs that have been superseded but old code remains
   - Spot migration patterns that are incomplete (e.g., mixing old/new patterns)
   - Identify error handling patterns that don't match current standards
   - Find temporary workarounds marked `TODO`, `FIXME`, `HACK` that should be addressed
   - Detect type `any` usages and `as unknown as T` casts violating strict typing

4. **Directory Structure & Organization (15% focus)**
   - Evaluate frontend flattening (`adr-0055`) effectiveness
   - Assess `src/domain/`, `src/ai/`, `src/lib/` organization efficiency
   - Identify misplaced files or unclear logical boundaries
   - Spot opportunities to consolidate related features
   - Evaluate DSL organization and naming clarity

5. **Code Smells & Anti-patterns (12% focus)**
   - Excessive context passing (prop drilling in React)
   - Overly complex component hierarchies
   - Side effects in unexpected places
   - Inconsistent error handling patterns
   - Over-abstraction (11-level deep folder structures)
   - AI-generated boilerplate code that could be simplified
   - Inconsistent naming conventions

6. **Build & Bundle Optimization (5% focus)**
   - Identify unnecessary transpilation or processing
   - Spot unused CSS or styling bloat
   - Recommend dynamic imports for code splitting opportunities
   - Check for large dependencies that could be replaced
   - Assess `cacheComponents` impact and efficacy

7. **Testing & Quality Gates (3% focus)**
   - Incomplete test coverage in critical paths
   - Test organization mismatches with source structure
   - Mocking patterns that could be improved or consolidated

---

## Analysis Methodology

For **each finding**, provide:

1. **Category**: Which of the 7 areas above
2. **Severity**: CRITICAL (blocks scalability/causes bugs), HIGH (significant debt/complexity), MEDIUM (improves maintainability), LOW (nice-to-have polish)
3. **Location(s)**: Exact file paths and line numbers/functions (use format `file.ts:123`)
4. **Current State**: What the code does now (concise)
5. **Problem**: Why it's sub-optimal
6. **Impact**: User experience, maintenance cost, performance, cognitive load
7. **Recommendation**: Specific, actionable fix with library/pattern to use
8. **Effort**: XS / S / M / L (relative to other changes)
9. **Dependencies**: Other fixes that should land first
10. **Evidence**: Reference to AGENTS.md, CLAUDE.md, or official docs backing the recommendation

---

## Investigation Framework

### 1. Duplication Detection
- Search for similar handler patterns in `src/app/api/**`
- Compare Zod schema definitions across `@schemas/*`
- Audit component file names for repeated suffixes (e.g., multiple `-wrapper`, `-layout` components)
- Identify near-identical form patterns in `src/components/ui/form`
- Check for duplicate utility functions in `src/lib/**`

### 2. Library Audit
- Trace `@ai-sdk/*` usage: Are all v6 primitives (`streamText`, `generateObject`, `convertToModelMessages`) used correctly?
- Audit Zod: Are we using v4-only APIs (top-level `z.email()`, `z.strictObject()`, etc.) or old v3 patterns?
- Zustand: Middleware order, store organization, computed properties usage
- React Query: Caching strategies, stale time, refetch behavior
- Supabase SSR: Are we using `createServerSupabase()` consistently in all server code?
- Rate limiting: Is `@upstash/ratelimit` + Redis initialized per-request properly?
- Security: Are random IDs always from `@/lib/security/random` (never `Math.random` or direct `crypto`)?

### 3. Obsolete Code Detection
- Cross-reference all ADRs (especially superseded ones) with implementation
- Find code paths mentioned in old ADRs that newer ADRs contradict
- Identify fallback implementations for features that have standardized
- Look for disabled/commented-out code that's been dead for months
- Spot test files for deleted features
- Check for polyfills or shims no longer needed

### 4. Organization Audit
- Verify `src/domain/schemas` is the single source of truth for all Zod definitions
- Check that all AI/tool code lives in `src/ai/` consistently
- Audit `src/lib/` for misplaced feature code (should be in domain or components)
- Verify imports use correct path aliases per AGENTS.md section 4.2
- Confirm no barrel exports (`export *`) or nested index re-exports
- Validate `src/app/api/**` route structure matches REST/RPC patterns clearly

### 5. Code Smell Analysis
- Highlight components with excessive prop drilling (>5 levels deep without context)
- Find rendering functions embedded in event handlers or conditionals
- Spot deeply nested ternary operators or switch statements
- Identify functions with multiple responsibilities (violates SRP)
- Flag error handling that swallows errors or logs without context
- Find AI-generated patterns: overly verbose boilerplate, redundant comments, repeated variable names

### 6. Build Performance
- Identify unused imports or tree-shaking failures
- Spot large dependencies in the bundle (check import size of @ai-sdk/*, zod, zustand)
- Find candidates for dynamic imports (lazy route components, non-critical features)
- Assess SVG handling and image optimization
- Check for excessive CSS rule duplication from Tailwind + CVA

### 7. Test Coverage Analysis
- Identify critical functions without tests (auth, payment, search)
- Find test files with poor naming or organization
- Spot mocking patterns that duplicate setup code
- Assess MSW handler centralization

---

## Output Format

Produce a **detailed markdown report** organized as follows:

```
# TripSage AI Repository Analysis Report

## Executive Summary
- X total findings across Y severity levels
- Estimated refactoring effort: Z weeks/sprints
- Highest-impact areas to focus first
- Quick wins (low effort, high impact)

## Findings by Category

### 1. Code Duplication & Consolidation (N findings)
[For each finding, use the structure from Analysis Methodology above]

- **[Specific Duplication Name]**
  - **Severity**: HIGH | **Effort**: M
  - **Location(s)**: file1.ts:123, file2.ts:456
  - **Current**: ...
  - **Problem**: ...
  - **Impact**: ...
  - **Recommendation**: ...
  - **Evidence**: AGENTS.md section 4.1 - Library First Principles

### 2. Dependency Leverage & Library Optimization (N findings)
[Same structure]

### 3. Technical Debt & Obsolete Code (N findings)
[Same structure]

### 4. Directory Structure & Organization (N findings)
[Same structure]

### 5. Code Smells & Anti-patterns (N findings)
[Same structure]

### 6. Build & Bundle Optimization (N findings)
[Same structure]

### 7. Testing & Quality Gaps (N findings)
[Same structure]

## Implementation Recommendations (By Priority)

### Phase 1: High-Impact Quick Wins (Can start immediately)
[3-5 specific refactoring tasks with minimal dependencies]

### Phase 2: Foundational Cleanup (Enables other improvements)
[3-5 tasks that unblock further work]

### Phase 3: Architecture Optimization (Medium-long term)
[Structural reorganizations or major library shifts]

### Phase 4: Polish & Debt Reduction (Ongoing)
[Continuous improvement tasks]

## Cross-Cutting Observations

- Patterns that work well and should be replicated
- Inconsistencies that should be standardized
- Architectural decisions that have aged well vs. should reconsider

## Metrics & Success Indicators

- Current bundle size estimate (gzipped JS, CSS)
- Test coverage by category
- Technical debt score (before/after)
- Code duplication ratio (before/after)
```

---

## Investigation Checklist

Before producing the report, verify you have examined:

- [ ] **Route Handlers**: All files in `src/app/api/**`, identify patterns in error handling, DI setup, auth checks
- [ ] **Components**: Sample `src/components/**`, look for repeated patterns, prop drilling, unnecessary complexity
- [ ] **Schemas**: All `@schemas/*` files, check for duplication and v4 Zod compliance
- [ ] **Stores**: All `src/stores/**`, verify middleware ordering and proper use of computed properties
- [ ] **Utilities**: `src/lib/**`, identify functions that appear similar or redundant
- [ ] **Hooks**: `src/hooks/**`, check for custom logic that could use libraries
- [ ] **Tests**: Sample `src/**/__tests__` and `e2e/`, assess patterns and coverage
- [ ] **Config**: `biome.json`, `tsconfig.json`, `next.config.ts`, `vitest.config.ts`
- [ ] **ADRs**: Read both active and superseded ADRs, spot contradictions in code
- [ ] **Package.json**: Verify all dependencies are actually used and up-to-date

---

## Critical Guardrails

1. **No false positives**: Only flag genuine duplication or anti-patterns, not stylistic preferences
2. **Evidence-based**: Every recommendation must reference AGENTS.md, official docs, or patterns already in the codebase
3. **Respect decisions**: Acknowledge when complex patterns exist for good reasons (e.g., performance, compliance) before suggesting changes
4. **Actionable only**: Don't suggest refactors unless you can describe the exact new approach with code examples
5. **Favor library patterns**: When there's a choice, recommend patterns from the chosen libraries (AI SDK v6, Zod v4, Zustand v5)

---

## Deliverables

After completing analysis, produce a **separate detailed implementation prompts document** (`IMPLEMENTATION-PROMPTS.md`) containing:

**Each implementation prompt should be:**
- **Completely atomic**: Can be applied in any order (minimal/explicit dependencies noted)
- **Fully independent**: Can be run in a fresh Claude Code session
- **Detailed and exact**: Specific file paths, line numbers, exact code changes
- **Complete**: Includes all steps from investigation through verification (quality gates)
- **Properly formatted**: Copy-paste ready markdown blocks for Claude Code
- **Tool-integrated**: References relevant MCP tools, skills, and verification steps

**Prompt structure per task:**
1. Task ID and name
2. Scope: Files affected, expected lines changed
3. Investigation phase (grep/read instructions)
4. Implementation phase (exact code changes)
5. Verification phase (tests, type-checks, linting)
6. Rollback steps if needed

The prompts document will be the input to Claude Code for actual refactoring execution.

---

END OF ANALYSIS PROMPT

**PACKED REPOSITORY CONTEXT FOLLOWS:**
