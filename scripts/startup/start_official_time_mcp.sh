#!/bin/bash
# Start the official Time MCP server

echo "Starting official Time MCP server..."
PORT=${1:-3000}
LOCAL_TIMEZONE=${2:-$(timedatectl | grep "Time zone" | awk '{print $3}')}

npx uvx mcp-server-time --port $PORT --local-timezone $LOCAL_TIMEZONE

echo "Time MCP server exited with code $?"