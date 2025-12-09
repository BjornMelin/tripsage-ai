# AI Elements MCP Server

This document explains what the AI Elements MCP server provides, how to add it to common IDE agents, and how to leverage it within our Next.js + AI SDK v6 stack during development.

## What It Is
- Remote MCP endpoint that exposes the AI Elements component registry and documentation to MCP clients. Useful for quickly recalling component APIs, usage examples, and recommended patterns while building UI.
- No authentication for public component information.

Reference: v6.ai-sdk.dev/elements/mcp

## Add to MCP Clients

Claude Code / Claude Desktop / Cursor / Codex (generic stdio/remote):

Use `mcp-remote` pointing at the Elements registry:

```json
{
  "mcpServers": {
    "ai-elements": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://registry.ai-sdk.dev/api/mcp"]
    }
  }
}
```

Restart your client; verify `ai-elements` appears in the server list.

## Example Prompts (Dev Workflow)
- "List AI Elements chat components and show a code sample using PromptInput and Message."
- "Show styling tokens and spacing guidance for AI Elements with Tailwind v4."

Expected result: agent returns relevant component docs and code samples for immediate copy/paste into `src/components/ai-elements/` or pages.

## Notes
- AI Elements MCP provides documentation and examples only; it does not modify code. Use it to speed UI implementation and ensure consistency with the library’s latest guidance.

