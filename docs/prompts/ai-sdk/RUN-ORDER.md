# Run Order & Parallelization Plan for AI SDK v6 Migration Prompts

Overview

- This guide lists the execution order for all prompts under `docs/prompts/ai-sdk/`. It also indicates safe parallelization, dependencies, and when Python deletion is allowed. Run each prompt in a fresh Codex CLI session using the included persona and tool instructions.

Order & dependencies

1) 00-foundations-setup.md (must run first)
   - Blocks: 01, 02, 04, 07

2) 01-byok-routes-and-security.md (can run after 00)
   - Parallel with: 02, 03, 07
   - Provides: /api/keys routes

3) 02-provider-registry-and-resolution.md (after 00)
   - Parallel with: 01, 03, 07
   - Provides: registry used by chat

4) 03-token-budgeting-and-limits.md (after 00; parallel with above)
   - Provides: countTokens/clamp utilities

5) 04-chat-api-sse-and-nonstream.md (depends on 02, 03; 00 done)
   - Uses: registry + token budgeting

6) 05-tools-and-mcp-integration.md (after 04 recommended; can start after 02)
   - Integrates into chat routes once ready

7) 06-memory-and-checkpoints.md (after 04; optional LangGraph JS)
   - Dep: 03 for token-window selection

8) 07-ui-ai-elements-integration.md (after 00; can run in parallel with 01–03)
   - Later wires to 04 once chat routes exist

9) 08-observability-telemetry-redaction.md (after 01, 04)
   - Adds spans/counters/redaction

10) 09-provider-openrouter-attribution.md (after 02)
    - Ensures headers present for OpenRouter

11) 10-optional-ai-gateway-adoption.md (feature flag; optional; after 02)

12) 11-testing-vitest-and-e2e.md (ongoing; consolidate tests from 02–07)

13) 12-decommission-python-cleanup.md (final)
    - Only after all above pass and parity confirmed

Parallelization notes

- Safe in parallel: 01, 02, 03, 07 (they modify distinct areas)
- Avoid running 04 and 05 concurrently until 04 scaffolds chat routes; then 05 can plug tools
- 08 depends on 01 + 04 to instrument meaningful spans

Acceptance gates before decommission

- All Next.js routes green; Vitest coverage for registry/BYOK/chat/tools/memory
- Observability present; rate limits enforced; attribution headers for OpenRouter
