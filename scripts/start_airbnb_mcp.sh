#!/bin/bash
# Start the Airbnb MCP server
# This script starts the OpenBnB Airbnb MCP server for use with TripSage.

# Determine script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Display banner
echo "====================================="
echo "  Starting Airbnb MCP Server"
echo "====================================="
echo "Server: OpenBnB MCP Server (Airbnb)"
echo "Version: $(npm view @openbnb/mcp-server-airbnb version)"
echo "====================================="

# Execute the MCP server with optional flags
# By default, we respect robots.txt. Use --ignore-robots-txt to bypass.
if [ "$1" == "--ignore-robots-txt" ]; then
  echo "NOTICE: Running with --ignore-robots-txt flag (bypassing robots.txt)"
  mcp-server-airbnb --ignore-robots-txt
else
  echo "NOTICE: Respecting robots.txt restrictions"
  mcp-server-airbnb
fi