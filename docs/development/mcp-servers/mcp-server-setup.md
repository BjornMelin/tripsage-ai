# MCP Server Setup Guide

This guide documents the required steps to attach the core MCP servers (Next.js built-in MCP, Vercel MCP, Supabase MCP) and optional additions (Next DevTools MCP, Upstash MCP, Playwright MCP) to OpenAI Codex, Cursor, and Claude Code. Instructions assume macOS/Linux shells; adapt paths as needed.

---

## Prerequisites

- Node.js ≥ 18 and PNPM installed.
- Tripsage AI frontend checked out locally.
- For Supabase MCP: personal access token (PAT) scoped to the target project and project reference ID.
- Ensure secrets are stored outside source control; use shell environment managers or credential stores.

---

## 1. Next.js Built-in MCP Server (Dev-only)

### 1.1 Start the dev server

```bash
pnpm dev
```

Keep the process running; the built-in MCP server is exposed automatically in development.

### 1.2 Confirm agent connectivity

- Keep the dev server running while IDE agents connect; the built-in MCP endpoint is available at `http://localhost:3000/_next/mcp`.
- Optional tooling such as Next DevTools MCP can be layered on top to provide documentation lookups and guided migrations (see §4.1).

---

## 2. Vercel MCP (Remote, OAuth-protected)

### 2.1 Authorize Vercel MCP

1. Ensure you have access to the Vercel team/project.
2. On first connection each client will open a browser window to complete OAuth; approve only the required scopes.

### 2.2 Client configuration

#### Claude Code

```bash
claude mcp add --transport http vercel https://mcp.vercel.com
```

Run `/mcp` inside Claude Code to trigger OAuth.

#### Cursor

1. `Settings → MCP → Add new MCP Server`
2. Type: `http`
3. URL: `https://mcp.vercel.com`
4. Save; follow the OAuth prompt.

#### OpenAI Codex

Edit `~/.codex/config.toml`:

```toml
[mcp_servers.vercel]
type = "streamable-http"
url = "https://mcp.vercel.com"
```

Restart Codex. The first request opens a browser window for authentication.

### 2.3 Recommended practices

- Use distinct connector names per project (e.g., `vercel-tripsage-prod`).
- Revoke tokens from the Vercel dashboard if a workstation is decommissioned.

---

## 3. Supabase MCP (Project-scoped, Read-only)

### 3.1 Prepare environment variables

```bash
export SUPABASE_ACCESS_TOKEN="pat-from-dashboard"
export SUPABASE_PROJECT_REF="your-project-ref"
```

Keep the PAT outside dotfiles or scripts committed to git.

### 3.2 Client configuration

#### Claude Code

```bash
SUPABASE_ACCESS_TOKEN="$SUPABASE_ACCESS_TOKEN" \
claude mcp add supabase \
  npx -y @supabase/mcp-server-supabase@latest \
  --read-only \
  --project-ref="$SUPABASE_PROJECT_REF"
```

#### Cursor

1. `Settings → MCP → Add new MCP Server`
2. Type: `command`
3. Command: `npx`
4. Arguments: `-y @supabase/mcp-server-supabase@latest --read-only --project-ref=$SUPABASE_PROJECT_REF`
5. Add environment variable `SUPABASE_ACCESS_TOKEN` via the advanced options dialog.

#### OpenAI Codex

Edit `~/.codex/config.toml`:

```toml
[mcp_servers.supabase]
command = "npx"
args = [
  "-y",
  "@supabase/mcp-server-supabase@latest",
  "--read-only",
  "--project-ref=${env:SUPABASE_PROJECT_REF}"
]

[mcp_servers.supabase.env]
SUPABASE_ACCESS_TOKEN = "${env:SUPABASE_ACCESS_TOKEN}"
```

Reload Codex after exporting the environment variables in your shell profile.

### 3.3 Operational notes

- Default to `--read-only` for day-to-day development; remove only when write tooling is explicitly required.
- Rotate PATs periodically and track usage in Supabase dashboard audit logs.

---

## 4. Optional MCP Servers

### 4.1 Next DevTools MCP (Developer Enablement)

- Purpose: auto-discovers local Next.js dev servers, surfaces runtime diagnostics (`get_errors`, `get_logs`, `get_page_metadata`), and supplies guided upgrade/playbook tooling.
- Prerequisite: run `pnpm dev` so the built-in Next.js MCP endpoint is reachable at `/_next/mcp`.

#### Claude Code

```bash
claude mcp add next-devtools \
  npx -y next-devtools-mcp@latest
```

#### Cursor

1. `Settings → MCP → Add new MCP Server`
2. Type: `command`
3. Command: `npx`
4. Arguments: `-y next-devtools-mcp@latest`
5. Save; verify `next-devtools` shows as connected while the dev server is running.

#### OpenAI Codex

Edit `~/.codex/config.toml`:

```toml
[mcp_servers.next_devtools]
command = "npx"
args = ["-y", "next-devtools-mcp@latest"]
```

Increase `startup_timeout_ms` if Codex starts slowly on Windows. Restart Codex to load the server.

> Usage tip: keep the Next DevTools pane open while performing codemods or Cache Components migrations; agents can interleave documentation links with live telemetry from the dev server.

> Browser testing: Next DevTools integrates with Playwright MCP for visual verification. To enable these actions, also install the Playwright MCP server (see `browser-automation/playwright-mcp.md`). Without Playwright MCP, runtime diagnostics and knowledge base features still work.

### 4.2 Upstash MCP (Rate Limiting & Redis Operations)

- Purpose: manage Upstash Redis databases, inspect limiter usage, and administer backups directly from IDE agents.[^upstash]
- Prerequisites:

  ```bash
  export UPSTASH_EMAIL="your-upstash-email"
  export UPSTASH_API_KEY="your-upstash-api-key"
  ```

#### Claude Code

```bash
UPSTASH_EMAIL="$UPSTASH_EMAIL" \
UPSTASH_API_KEY="$UPSTASH_API_KEY" \
claude mcp add upstash \
  npx -y @upstash/mcp-server@latest \
  --email "$UPSTASH_EMAIL" \
  --api-key "$UPSTASH_API_KEY"
```

#### Cursor

1. `Settings → MCP → Add new MCP Server`
2. Type: `command`
3. Command: `npx`
4. Arguments: `-y @upstash/mcp-server@latest --email=$UPSTASH_EMAIL --api-key=$UPSTASH_API_KEY`
5. Add `UPSTASH_EMAIL` and `UPSTASH_API_KEY` via the environment editor; mark as masked.

#### OpenAI Codex

Edit `~/.codex/config.toml`:

```toml
[mcp_servers.upstash]
command = "npx"
args = [
  "-y",
  "@upstash/mcp-server@latest",
  "--email", "${env:UPSTASH_EMAIL}",
  "--api-key", "${env:UPSTASH_API_KEY}"
]
```

Export the variables in your shell and restart Codex. For remote deployments, run the server with HTTP transport:

```bash
npx @upstash/mcp-server@latest \
  --transport http \
  --port 3030 \
  --email "$UPSTASH_EMAIL" \
  --api-key "$UPSTASH_API_KEY"
```

Then point clients at `http://localhost:3030/mcp`.

> Usage tip: create separate MCP entries per environment (`upstash-dev`, `upstash-prod`) to isolate quotas and avoid accidental production mutations.

### 4.3 Playwright MCP (Browser Automation)

- Purpose: drive Tripsage UI flows through Playwright’s accessibility tree, enabling agents to reproduce bugs and author regression scripts.[^playwright]
- Prerequisites: Node.js ≥ 18 and Playwright dependencies (`npx playwright install`) available on the host.

#### Claude Code

```bash
claude mcp add playwright \
  npx @playwright/mcp@latest
```

Append `--browser chromium` (or `firefox`, `webkit`) if you want to pin a browser.

#### Cursor

1. `Settings → MCP → Add new MCP Server`
2. Type: `command`
3. Command: `npx`
4. Arguments: `@playwright/mcp@latest --browser=chromium`
5. Save; confirm Cursor launches the MCP in a dedicated terminal.

#### OpenAI Codex

Edit `~/.codex/config.toml`:

```toml
[mcp_servers.playwright]
command = "npx"
args = ["@playwright/mcp@latest", "--browser=chromium"]
```

Restart Codex. If the server requires cached browsers, run `npx playwright install chromium` beforehand.

> Usage tip: script CI jobs that start Playwright MCP in headless mode and let agents request targeted smoke tests before merges.

### 4.4 Apify MCP (Structured Data Extraction)
- Purpose: run Apify Actors for scraping/data extraction; complements browser automation.

#### Remote (OAuth preferred)
```json
{ "mcpServers": { "apify": { "url": "https://mcp.apify.com" } } }
```
Or with token header:
```json
{ "mcpServers": { "apify": {
  "url": "https://mcp.apify.com",
  "headers": { "Authorization": "Bearer <APIFY_TOKEN>" }
} } }
```

#### Local (stdio)
```bash
export APIFY_TOKEN="<your-apify-token>"
npx -y @apify/actors-mcp-server
```

> Usage tip: keep actor usage scoped per project and monitor costs; prefer OAuth where supported.

---

## 5. Verification Checklist

1. Start the TripSage dev server (`pnpm dev`) before opening IDE agents.
2. Confirm each MCP server appears in the client’s MCP list without warnings.
3. Run a simple tool from each server:
   - Next DevTools: `get_page_metadata`
   - Vercel MCP: `list_projects`
   - Supabase MCP: `list_tables`
   - Upstash MCP (optional): `redis_database_list_databases`
   - Playwright MCP (optional): `navigate_to_url`
   - Apify MCP (optional): list available actors or tools
   - AI Elements MCP (optional): "List available AI Elements chat components"
4. Document any additional scopes or environment variables in the team runbook.

---

## 6. Maintenance

- Monitor upstream release notes for each MCP package and schedule periodic updates.
- Revalidate OAuth grants quarterly.
- If secrets change, update local environment variables and restart MCP processes (Upstash API keys, Supabase PATs, Playwright browser caches).

## 7. Additional References

- AI Elements MCP: `docs/development/mcp-servers/ai-elements-mcp.md`
- Browser automation overview: `docs/development/mcp-servers/browser-automation/overview.md`
- Browserbase MCP: `docs/development/mcp-servers/browser-automation/browserbase-mcp.md` (export `BROWSERBASE_API_KEY` and `BROWSERBASE_PROJECT_ID` before running the server)
- Playwright MCP: `docs/development/mcp-servers/browser-automation/playwright-mcp.md`
- Browser-Use MCP: `docs/development/mcp-servers/browser-automation/browser-use-mcp.md`
- Decision Matrix: `docs/development/mcp-servers/browser-automation/decision-matrix.md`
- Apify MCP: `docs/development/mcp-servers/browser-automation/apify-mcp.md`

[^upstash]: Upstash MCP Server README. <https://raw.githubusercontent.com/upstash/mcp-server/main/README.md>
[^playwright]: Playwright MCP README. <https://raw.githubusercontent.com/microsoft/playwright-mcp/main/README.md>
