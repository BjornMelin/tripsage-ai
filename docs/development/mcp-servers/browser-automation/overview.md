# Browser Automation MCPs: Overview

This overview compares Playwright MCP, Browserbase (Stagehand) MCP, and Browser-Use MCP for Tripsage AI development workflows. Use this to select the right tool per task. Note: Next DevTools MCP can orchestrate browser testing via Playwright MCP, but it does not ship Playwright tools; install the Playwright MCP server to access those actions.

## Options
- Playwright MCP: deterministic, accessibility-tree driven, local/CI friendly.
- Browserbase Stagehand MCP: managed cloud browsers with Stagehand agentic actions; proxy/fingerprint/stealth built-in; SHTTP and stdio.
- Browser-Use MCP: local autonomous/direct control via `uvx browser-use --mcp` (Python-first); quick experiments and ad-hoc automation.
- Apify MCP (complementary): structured actors for data extraction via `mcp.apify.com`. See `apify-mcp.md`.

## When to Use What
- Local dev + deterministic smoke tests → Playwright MCP.
- Interactive browsing at scale, anti-bot, multi-session resilience → Browserbase Stagehand MCP.
- Fast local trials or PoCs with autonomous flows → Browser-Use MCP.
- Bulk structured scraping or catalog data → Apify MCP; pair with others.

See decision-matrix.md for weighted scoring and rationale.
