# Technical Debt Ledger — Resolved Items (2025-11-15)

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
