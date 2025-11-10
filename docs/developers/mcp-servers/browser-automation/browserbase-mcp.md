# Browserbase (Stagehand) MCP Server

Managed cloud browser automation with Stagehand. Best for production-like browsing, anti-bot resilience, and session observability.

References: docs.stagehand.dev/v3/integrations/mcp/introduction, docs.browserbase.com/integrations/mcp/setup, github.com/browserbase/mcp-server-browserbase

## Credentials
- Browserbase API key, Project ID (dashboard).

## Installation Methods

Remote (SHTTP via Smithery):
```json
{
  "mcpServers": {
    "browserbase": {
      "type": "streamable-http",
      "url": "<smithery-hosted-url>"
    }
  }
}
```

STDIO (local): ensure credentials are available
```bash
export BROWSERBASE_API_KEY="<api-key>"
export BROWSERBASE_PROJECT_ID="<project-id>"
npx -y @browserbasehq/mcp
```

## Usage Examples
- "Open google.com, search for ‘Paris hotels’, return top 3 links with titles and prices."
- "Navigate to example.com, fill contact form, and submit; capture screenshot."

## Strengths / Risks
- Strengths: managed sessions, proxies/stealth, session replay/HAR, higher success on modern JS sites.
- Risks: vendor cost and lock-in; mitigate via MCP abstractions and a Playwright fallback.

## Cost Notes
- Developer plan advertises ~100 hours/month and bundled proxy quota; overage per-hour and per-GB proxy. See browserbase.com/pricing.
