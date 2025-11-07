# MCP Servers Research Tasks and Implementation Roadmap

This roadmap links our MCP documentation to actionable implementation steps and the prompts under `docs/prompts/ai-sdk/`.

## Phase A — MCP Enablement
- AI Elements MCP
  - Add to IDE via `mcp-remote` (registry endpoint).
  - Adopt during UI work; reference `07-ui-ai-elements-integration.md` for component selections.
- Browser Automation
  - Start with Playwright MCP locally for dev tests.
  - Add Browserbase Stagehand MCP for production-like browsing in later QA.
  - Optional Browser-Use MCP for quick PoCs.
  - Optional Apify MCP for structured datasets (SERPs, catalogs) complementing browsing.
- Apify MCP (optional complement)
  - Configure OAuth or token as needed for catalog data ingestion.

## Phase B — AI SDK Prompts Alignment
- Map prompts to implementation:
  - 00–04: Verify Next.js route handlers, SSE/non-stream, provider registry.
  - 05: Tools and MCP integration — wire `experimental_createMCPClient` where appropriate.
  - 06–07: Memory/checkpoints and UI Elements usage in chat flows.
  - 11: Vitest and e2e — integrate Playwright MCP smoke validations.
  - 12: Python decommission — plan TS parity tasks.

## Phase C — Dev Workflow Integrations
- IDE presets per environment (dev/stage/prod) for MCP entries.
- Runtimes and secrets: centralize API keys and env docs.
- Add how-to snippets to app routes for MCP tool calls (without committing secrets).

## Acceptance Checklist
- MCP servers installed and verified.
- Decision matrix reviewed and accepted.
- Prompts check-off started; record progress inline in prompt files.
