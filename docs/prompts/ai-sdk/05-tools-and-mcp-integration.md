# Prompt: Tools & MCP Integration (Zod Tools + Model Context Protocol)

Executive summary

- Goal: Port Python tool invocation to AI SDK v6 tools and optionally MCP tools. Define Zod schemas and execute handlers for each tool; build a tool registry that can be passed to `streamText`.

Custom persona

- You are “AI SDK Migrator (Tools/MCP)”. You reduce glue by using AI SDK native tool patterns and MCP for external systems.

Docs & references

- Tool Calling: <https://v6.ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling>
- MCP Tools: <https://v6.ai-sdk.dev/docs/ai-sdk-core/mcp-tools>
- exa.crawling_exa both pages; firecrawl_scrape for single-page detail
- exa.get_code_context_exa for Zod tool examples; exa.web_search_exa for MCP patterns
- zen.planner; zen.thinkdeep + zen.analyze; zen.consensus for tool registry design (≥ 9.0/10)
- zen.secaudit (tool executions must not leak secrets); zen.challenge; zen.codereview

Plan (overview)

1) `frontend/lib/tools/index.ts` exports:
   - Local tools: Zod schema + execute
   - MCP tools: configured endpoints; same interface
2) Update chat routes to accept a set of tools and pass to `streamText`
3) Vitest tests: unit for each tool; integration to ensure tool calls interleave correctly in stream

Checklist (mark off; add notes under each)

- [ ] Implement `frontend/lib/tools/index.ts` with Zod schemas and execute handlers
  - Notes:
- [ ] Configure MCP tools alongside local tools with unified interface
  - Notes:
- [ ] Wire tools usage into chat stream calls
  - Notes:
- [ ] Vitest tests: unit for tools; integration to verify interleaving
  - Notes:
- [ ] Write ADR(s) and Spec(s) for tools/MCP registry
  - Notes:

Working instructions (mandatory)

- Check off tasks only after Vitest/biome/tsc are clean.
- Add “Notes” for implementation details, issues, and debt; address or log.
- Author ADR(s) in `docs/adrs/` describing tool registry design, MCP boundaries, and security; create Spec(s) in `docs/specs/` defining tool schemas and execution contracts.

Process flow (required)

1) Research: exa.web_search_exa → exa.crawling_exa → firecrawl_scrape → exa.get_code_context_exa for Zod tools and MCP.
2) Plan: zen.planner; list atomic tasks.
3) Deep design: zen.thinkdeep + zen.analyze for tool registry design and security.
4) Decide: zen.consensus (≥ 9.0/10); revise if necessary.
5) Draft docs: ADR(s)/Spec(s) for tools and MCP contracts.
6) Security review: zen.secaudit (no secrets leakage; timeouts; idempotency).
7) Implement: code + tests; keep Biome/tsc clean.
8) Challenge: zen.challenge assumptions.
9) Review: zen.codereview; fix; rerun checks.
10) Finalize docs: update ADR/Spec with deltas.

Legacy mapping (delete later)

- Remove Python tool-calling utilities and any LangChain-specific tool binding in orchestrator nodes

Testing requirements

- Validate schema enforcement; simulate tool errors; ensure robust error handling

Final Notes & Next Steps (compile from task notes)

- Summary of changes and decisions:
- Outstanding items / tracked tech debt:
- Follow-up prompts or tasks:

Additional context & assumptions

- Local tool pattern example:
  - `const tool = { parameters: z.object({...}), execute: async (args, ctx) => { ... } }`
- MCP tool config: define endpoint, auth (server-only), and target capability; do not persist secrets in tool outputs.
- Tool execution must be idempotent where possible; add timeouts and surface clear error messages to the LLM.
- Consider a tool registry module exposing `{ name, description, parameters, execute }` for each tool.

File & module targets

- `frontend/lib/tools/index.ts` (export arrays/maps of tools)
- `frontend/lib/tools/types.ts` (types for tool interfaces)

Testing & mocking guidelines

- Unit-test schemas validation (invalid payloads rejected); ensure execution returns expected shapes.
- Integration-test streamed tool calls: ensure tool results are included in final model output.
