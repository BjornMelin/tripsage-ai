# Prompt: Decommission Python/FastAPI Codepaths After Parity

## Executive summary

- Goal: After all AI SDK v6 features are live and tests are green, delete superseded Python/FastAPI runtime paths and tests. Keep only final implementations.

## Custom persona

- You are “AI SDK Migrator (Cleanup)”. You remove legacy with precision.

## Deletion/refactor mapping (final-only)

- Delete Python chat/BYOK endpoints and helpers:
  - `tripsage/api/routers/chat.py`
  - `tripsage/api/routers/keys.py`
  - `tripsage_core/services/business/chat_service.py`
  - `tripsage_core/services/external_apis/llm_providers.py`
  - Any Python adapters/wrappers introduced for LLM runtime
  - Orchestrator modules that bind LangChain clients at runtime (conditional if LangGraph JS replaces them): `tripsage/orchestration/*`
- Remove tests that validated Python chat/BYOK/tool paths:
  - `tests/integration/api/test_chat_streaming.py` (migrate to Next tests)
  - `tests/unit/external/test_llm_providers.py` and similar provider tests
  - Orchestration tests tied to LangChain LLM client calls

## Plan (overview)

1) Confirm all Next.js routes + Vitest suites green
2) Remove files listed above
3) Update CI to drop Python jobs related to removed modules
4) zen.codereview for the removal diff; ensure no references remain

## Checklist (mark off; add notes under each)

- [ ] Verify parity and green tests (routes + Vitest)
  - Notes:
- [x] Delete Python/FastAPI codepaths and tests listed above
  - Notes:
- [ ] Update CI to remove obsolete jobs
  - Notes:
- [ ] Run zen.codereview for final diff
  - Notes:
- [ ] Write ADR(s) and Spec(s) capturing decommission rationale and scope
  - Notes:

### Augmented checklist (docs and snapshots)

- [ ] Update documentation to remove references to `/api/chat/*` Python endpoints
- [ ] Regenerate OpenAPI snapshot to reflect removed endpoints

## Working instructions (mandatory)

- Check off tasks only after Vitest/biome/tsc are clean and CI is adjusted.
- Add “Notes” per task; address or log follow-ups.

Validation

- Repo builds with Next.js API only for these features; no import errors from removed modules
- Use zen.analyze to confirm no remaining references.
- Run zen.codereview on removal diff.
- Use zen.secaudit to ensure decommission does not alter security posture unintentionally.
- If disputes, use zen.challenge.
- Write ADR(s) under `docs/adrs/` documenting rationale and scope of removal; author Spec(s) under `docs/specs/` for the decommission steps, CI changes, and verification.

## Process flow (required)

1) Research: exa.web_search_exa → exa.crawling_exa → firecrawl_scrape for decommission best practices; verify internal references.
2) Plan: zen.planner; list exact files and CI updates.
3) Deep design: zen.thinkdeep + zen.analyze to confirm impact and side effects.
4) Decide: zen.consensus (≥ 9.0/10) on timing and scope.
5) Draft docs: ADR(s)/Spec(s) for removal plan.
6) Security review: zen.secaudit to ensure posture unaffected.
7) Implement: removal; update CI; keep checks green.
8) Challenge: zen.challenge if concerns remain.
9) Review: zen.codereview; fix; rerun checks.
10) Finalize docs: update ADR/Spec with outcomes.

## Additional context & assumptions

- Verification checklist before deletion:
  - Grep repo for imports/references to `tripsage/api/routers/chat.py`, `tripsage/api/routers/keys.py`, `tripsage_core/services/business/chat_service.py`, provider wrappers, and orchestrator LangChain LLM usages.
  - Ensure CI/QA pipelines no longer run Python tests for these features.
  - Docs updated to point to Next.js API.

## File targets to remove (double-check with grep before rm)

- `tripsage/api/routers/chat.py`
- `tripsage/api/routers/keys.py`
- `tripsage_core/services/business/chat_service.py`
- `tripsage_core/services/external_apis/llm_providers.py`
- Any orchestration files that directly instantiate LangChain LLM clients (retained only if still required for non-LLM flows)
- Tests that cover the above paths exclusively
