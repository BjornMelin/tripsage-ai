# TripSage MCP Servers Configuration

This directory contains the configuration and dependencies for MCP servers used by TripSage.

## Included Servers

- **Airbnb MCP Server**: Integration with Airbnb for accommodation search and listing details

## Setup

1. Install Node.js dependencies:

   ```bash
   cd mcp_servers
   npm install
   ```

2. Configure Claude Desktop:

Copy the `claude_desktop_config.json` content to your Claude Desktop configuration.

## Development Configuration

For development environments where you need to bypass robots.txt restrictions:

```json
{
  "mcpServers": {
    "airbnb": {
      "command": "npx",
      "args": ["-y", "@openbnb/mcp-server-airbnb", "--ignore-robots-txt"]
    }
  }
}
```

## Deployment

For production deployment, consider using a Docker container or a more persistent solution rather than relying on `npx` to fetch the package each time.
