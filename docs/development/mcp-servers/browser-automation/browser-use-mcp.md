# Browser-Use MCP Server

Local browser automation via the `browser-use` project with MCP exposure; good for quick demos and ad-hoc tasks.

Reference: docs.browser-use.com/customize/integrations/mcp-server

## Start MCP Server (stdio)
```bash
uvx browser-use --mcp
```

Claude Desktop config (macOS):
```json
{
  "mcpServers": {
    "browser-use": {
      "command": "uvx",
      "args": ["browser-use", "--mcp"],
      "env": { "OPENAI_API_KEY": "<key>" }
    }
  }
}
```

## Tools
- Direct control: navigate, click, type, scroll, get_state.
- Agent tool: retry_with_browser_use_agent for autonomous flows.

## Strengths / Risks
- Strengths: fast to start locally; autonomous mode; minimal setup.
- Risks: Python-first; lacks managed stealth/proxies; reliability varies on consumer sites.

