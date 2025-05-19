#!/bin/bash
# Stop the Airbnb MCP server
# This script stops the OpenBnB Airbnb MCP server running for TripSage.

# Display banner
echo "====================================="
echo "  Stopping Airbnb MCP Server"
echo "====================================="

# Find and kill the MCP server process
PID=$(pgrep -f "mcp-server-airbnb")

if [ -z "$PID" ]; then
  echo "No running Airbnb MCP server found."
  exit 0
else
  echo "Found Airbnb MCP server process with PID: $PID"
  kill $PID
  
  # Verify termination
  sleep 1
  if kill -0 $PID 2>/dev/null; then
    echo "Server still running, sending SIGKILL..."
    kill -9 $PID
    sleep 1
  fi
  
  if kill -0 $PID 2>/dev/null; then
    echo "WARNING: Could not terminate server process."
    exit 1
  else
    echo "Airbnb MCP server stopped successfully."
    exit 0
  fi
fi