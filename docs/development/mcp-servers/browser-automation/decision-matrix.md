# Browser Automation MCP Decision Matrix

Weights: Solution Leverage 35%, Application Value 30%, Maintenance Load 25% (higher = lower burden), Adaptability 10%.

| Option | Leverage | Value | Maintenance | Adaptability | Weighted |
|--------|----------|-------|------------|--------------|----------|
| Browserbase Stagehand MCP | 9.5 | 9.0 | 9.0 | 8.5 | 9.13 |
| Apify MCP (complement) | 8.7 | 8.8 | 9.2 | 8.2 | 8.81 |
| Browser-Use MCP | 8.8 | 8.5 | 7.0 | 8.5 | 8.23 |
| Playwright MCP | 8.5 | 8.8 | 6.5 | 8.0 | 8.04 |
| mcp-chrome | 7.5 | 7.8 | 6.0 | 8.0 | 7.27 |

## Recommendations
- Primary: Browserbase Stagehand MCP for production-like flows and anti-bot resilience (≥9.0).
- Complement: Apify MCP for structured data extraction at scale.
- Development: Playwright MCP for local deterministic tests; Browser-Use for ad-hoc demos.

See each server’s dedicated doc for setup and examples.

Note: Next DevTools MCP integrates with Playwright MCP for browser steps; it does not bundle Playwright tools. Install Playwright MCP to enable those actions when using Next DevTools.
