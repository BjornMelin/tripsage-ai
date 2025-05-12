#!/bin/bash

echo "Stopping official Time MCP server..."
TIME_MCP_PIDS=$(ps aux | grep "[m]cp-server-time" | awk '{print $2}')

if [ -z "$TIME_MCP_PIDS" ]; then
    echo "No Time MCP server process found"
    exit 0
fi

for PID in $TIME_MCP_PIDS; do
    echo "Killing Time MCP server with PID: $PID"
    kill -9 $PID
done

echo "All Time MCP server processes terminated"