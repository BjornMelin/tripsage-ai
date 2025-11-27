# Playwright MCP Server

Playwright MCP provides deterministic browser automation via Playwright’s accessibility tree (no screenshots). Ideal for local development, CI smoke tests, and stable, authenticated dashboards.

## Add to MCP Clients

Claude Code:
```bash
claude mcp add playwright \
  npx @playwright/mcp@latest
```

Cursor:
1. Settings → MCP → Add new MCP Server
2. Type: command
3. Command: `npx`
4. Arguments: `@playwright/mcp@latest --browser=chromium`

Codex (Toml):
```toml
[mcp_servers.playwright]
command = "npx"
args = ["@playwright/mcp@latest", "--browser=chromium"]
```

## Usage Examples
- "Navigate to https://example.com and read the H1 text"
- "Click the login button and capture accessibility tree snapshot"

## Using with Next DevTools MCP
Next DevTools MCP can orchestrate Playwright MCP for browser testing and visual checks, but it does not include Playwright tools itself. After installing Playwright MCP in your MCP client, Next DevTools will detect and call its tools for browser steps while still providing diagnostics and knowledge-base features.

## Strengths / Risks
- Strengths: deterministic, easy local debugging, good for CI, no vendor lock-in.
- Risks: anti-bot/stealth/proxy rotation is DIY; less reliable on hostile consumer sites.
