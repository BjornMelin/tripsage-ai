# Technical Debt Ledger — Resolved Items (2025-10-31)

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
  - Fix: Verification task documented in operators guide (see docs/operators/supabase-configuration.md); ensure migrations applied. Pending ops runbook execution.
  - Status: Pending verification (staging/prod)

No outstanding technical debt items within the scope modified in this change set.
