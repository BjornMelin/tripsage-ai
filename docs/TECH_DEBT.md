# Technical Debt Ledger — Resolved Items (2025-11-18)

- Area: Frontend DRY Optimization (Test Consolidation)
  - Item: 7 duplicate `_shared.ts` test utility files across store and lib directories
  - Impact: Code duplication, maintenance overhead, inconsistent testing patterns
  - Risk: Test regressions from inconsistent utilities, developer confusion
  - Fix: Migrated all utilities to centralized `@/test/*` files - `store-helpers.ts`, `factories.ts`, `api-helpers.ts`, `schema-helpers.ts`, `component-helpers.tsx`
  - Status: Resolved

- Area: Chat Store Cross-Slice Dependencies
  - Item: `chat-messages.ts` directly calling `useChatMemory.getState()` violating slice isolation
  - Impact: Tight coupling between slices, testing complexity, architectural violations
  - Risk: Refactoring hazards, unexpected state interactions
  - Fix: Created `useChatActions` orchestrator hook for coordinated operations, removed direct slice coupling
  - Status: Resolved

- Area: Client-Server Boundary Violations
  - Item: Chat slices importing server-only QStash helpers directly from client code
  - Impact: Bundle size bloat, potential runtime errors, security boundary violations
  - Risk: Production failures, security issues, bundling problems
  - Fix: Created `/api/memory/sync` route handler, moved QStash logic server-side, updated slices to use REST API
  - Status: Resolved

- Area: AI SDK Integration Placeholders
  - Item: Chat store methods containing placeholder streaming implementations
  - Impact: Non-functional streaming, misleading code, development confusion
  - Risk: Production deployment with broken features
  - Fix: Implemented complete AI SDK v6 streaming via `/api/chat/send` and `/api/chat/stream` routes with proper UIMessage handling
  - Status: Resolved

- Area: URL Object Memory Leaks
  - Item: `URL.createObjectURL()` calls not being revoked in chat message handling
  - Impact: Memory leaks in long-running sessions, browser performance degradation
  - Risk: Application slowdown, crashes in extended usage
  - Fix: Added URL tracking and revocation in `clearMessages`, `deleteSession`, and attachment cleanup
  - Status: Resolved

- Area: Backend AI SDK v5 legacy code cleanup (FINAL-ONLY)
  - Item: Dead code remnants after AI SDK v6 migration - broken router imports, unused MemoryService/ConfigurationService references, legacy model fields
  - Impact: App startup failures, type checking errors, bloated codebase with unused imports
  - Risk: Runtime errors, maintenance overhead, confusion in codebase
  - Fix: Aggressively removed all dead code in single-pass cleanup - deleted broken imports, dead service instantiations, legacy fields, superseded tests
  - Status: Resolved

- Area: Chat streaming path (api/chat/stream)
  - Item: LangChain-based streaming with `ChatOpenAI.astream` in hot path
  - Impact: Extra dependency and indirection; harder error handling and SSE control
  - Risk: Streaming regressions; higher maintenance
  - Fix: Replaced with AI SDK v6 streaming (`streamText`), added BYOK provider resolution and SSE contract
  - Status: Resolved

- Area: Agent orchestration (migration to TypeScript)
  - Item: Python LangGraph orchestration system with complex agent nodes
  - Impact: High maintenance overhead; deployment complexity; limited scalability
  - Risk: Agent failures; complex debugging; deployment issues
  - Fix: Migrated all agent functionality to TypeScript AI SDK v6 with direct tool calling
  - Status: Resolved

- Area: Tests (streaming + BYOK)
  - Item: Missing contract/integration tests for SSE and BYOK branches
  - Impact: Refactors unsafe; regressions undetected
  - Risk: Production incidents on streaming
  - Fix: Added provider-mocked SSE tests covering delta/final/[DONE] and OpenRouter branch
  - Status: Resolved

- Area: Vault ops hardening (tracking)
  - Item: Verify role/ownership for Vault RPCs in non-dev
  - Impact: Privilege creep possible without verification
  - Fix: Created comprehensive verification documentation (docs/operators/supabase-configuration.md) and automated verification script (scripts/verify_vault_hardening.py). Migrations verified and runbook execution documented.
  - Status: Resolved

No outstanding technical debt items within the scope modified in this change set.
