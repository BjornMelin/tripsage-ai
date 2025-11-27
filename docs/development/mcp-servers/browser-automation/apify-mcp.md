# Apify MCP Server (Complementary)

Apify MCP lets agents run Actors for scraping/data extraction via a remote HTTPS endpoint or local stdio server.

References: https://docs.apify.com/platform/integrations/mcp, https://github.com/apify/apify-mcp-server

## Remote (Streamable HTTP)
OAuth (recommended):
```json
{ "mcpServers": { "apify": { "url": "https://mcp.apify.com" } } }
```

Token header (alternative):
```json
{ "mcpServers": { "apify": {
  "url": "https://mcp.apify.com",
  "headers": { "Authorization": "Bearer <APIFY_TOKEN>" }
} } }
```

## Local (stdio)
```bash
export APIFY_TOKEN="<your-apify-token>"
npx -y @apify/actors-mcp-server
```

## Usage Examples
- "List available Apify Actors I can run"
- "Run the Google SERP Actor for query 'Paris hotels' and summarize the top links"

## Strengths / Risks
- Strengths: huge catalog of ready-made actors; great for structured datasets.
- Risks: not a replacement for interactive browsing; actor selection and cost need governance.

