# Technical Debt Ledger — Resolved Items (2025-10-31)

- Area: Chat streaming path (api/chat/stream)
  - Item: LangChain-based streaming with `ChatOpenAI.astream` in hot path
  - Impact: Extra dependency and indirection; harder error handling and SSE control
  - Risk: Streaming regressions; higher maintenance
  - Fix: Replaced with OpenAI SDK streaming (`client.chat.completions.create(..., stream=True)`), added optional OpenRouter branch and SSE contract
  - Status: Resolved

- Area: Orchestrator nodes (fallback configs)
  - Item: Server-key-only fallbacks for LLM API key selection
  - Impact: Violates BYOK precedence; inconsistent behavior across nodes
  - Risk: Using platform key when user BYOK exists
  - Fix: Added BYOK resolution via `database_service.fetch_user_service_api_key(user_id, 'openai')` before settings fallback across nodes
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
