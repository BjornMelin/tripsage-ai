#!/bin/bash
# Script to stop the Google Calendar MCP server

# Find and kill the Google Calendar MCP server process
PID=$(ps aux | grep 'node.*build/index.js' | grep -v grep | awk '{print $2}')

if [ -n "$PID" ]; then
    echo "Stopping Google Calendar MCP server (PID: $PID)..."
    kill -15 $PID
    
    # Wait for the process to terminate
    for i in {1..5}; do
        if ! ps -p $PID > /dev/null; then
            echo "Google Calendar MCP server stopped successfully."
            exit 0
        fi
        echo "Waiting for server to terminate..."
        sleep 1
    done
    
    # Force kill if it's still running
    if ps -p $PID > /dev/null; then
        echo "Forcing termination of Google Calendar MCP server..."
        kill -9 $PID
        if ! ps -p $PID > /dev/null; then
            echo "Google Calendar MCP server forcefully terminated."
            exit 0
        else
            echo "Failed to terminate Google Calendar MCP server."
            exit 1
        fi
    fi
else
    echo "No running Google Calendar MCP server found."
fi