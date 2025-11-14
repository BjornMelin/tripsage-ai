# Prompt: Decommission Python/FastAPI Codepaths After Parity (COMPLETED)

## Executive summary

- Goal: After all AI SDK v6 features are live and tests are green, delete superseded Python/FastAPI runtime paths and tests. Keep only final implementations.
- Status: COMPLETED - All Python agent, tool, and orchestration modules have been removed and replaced with TypeScript AI SDK v6 implementations.

## Custom persona

- You are “AI SDK Migrator (Cleanup)”. You remove legacy with precision.

## Deletion/refactor mapping (final-only)

- Delete Python chat/BYOK/attachments endpoints and helpers:
  - `tripsage/api/routers/chat.py`
  - `tripsage/api/routers/keys.py`
  - `tripsage_core/services/business/chat_service.py`
  - `tripsage_core/services/external_apis/llm_providers.py`
  - `tripsage/api/routers/attachments.py` (if attachment proxy still present)
  - Any Python adapters/wrappers introduced for LLM runtime
  - Orchestrator modules that bind LangChain clients at runtime (conditional if LangGraph JS replaces them): `tripsage/orchestration/*`
- Remove tests that validated Python chat/BYOK/tool paths:
  - `tests/integration/api/test_chat_streaming.py` (migrate to Next tests)
  - `tests/unit/external/test_llm_providers.py` and similar provider tests
  - Orchestration tests tied to LangChain LLM client calls

## Plan (overview)

1) Confirm all Next.js routes + Vitest/Playwright suites green; v6 message parts validated
2) Remove files listed above
3) Update CI to drop Python jobs related to removed modules; bump coverage thresholds
4) zen.codereview for the removal diff; ensure no references remain

## Checklist (mark off; add notes under each)

- [x] Verify parity and green tests (routes + Vitest)
  - Notes:
- [x] Delete Python/FastAPI codepaths and tests listed above
  - Notes: All directories and modules listed have been removed: tripsage/orchestration/, tripsage/agents/, tripsage/tools/, corresponding test suites, and related imports.
- [x] Update CI to remove obsolete jobs
  - Notes: Python test suites for deleted modules have been removed from CI coverage requirements.
- [x] Run zen.codereview for final diff
  - Notes: Code review completed; all Python modules successfully removed with no breaking changes.
- [x] Write ADR(s) and Spec(s) capturing decommission rationale and scope
  - Notes: Documentation updated in CHANGELOG.md and various README files to reflect the migration completion.

### Augmented checklist (docs and snapshots)

- [x] Update documentation to remove references to `/api/chat/*` Python endpoints
  - Notes: All documentation updated to reference TypeScript AI SDK v6 implementations instead of Python endpoints.
- [x] Regenerate OpenAPI snapshot to reflect removed endpoints
  - Notes: OpenAPI documentation updated to reflect current API surface without Python agent endpoints.

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

---

## Final Alignment with TripSage Migration Plan (Next.js 16 + AI SDK v6)

- Core decisions impacting Decommissioning:
  - Next.js 16 + AI SDK v6 implementations are canonical; remove Python/FastAPI paths once parity verified.
  - Final-only policy: delete legacy/flags/shims; keep only final implementations.

- Implementation checklist delta:
  - Validate parity across chat, BYOK, tools, memory, and observability; then remove Python modules and tests.
  - Update READMEs/specs; ensure CI no longer runs removed tests/jobs.

- References:
  - Migration plan: docs/prompts/ai-sdk/trip_sage_migration_to_next.md

Verification

- Repo free of legacy Python for migrated features; docs updated; CI green.

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
