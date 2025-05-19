#!/bin/bash
# Stop script for the Time MCP server

# Check if PID file exists
if [ -f "./time_mcp.pid" ]; then
    TIME_MCP_PID=$(cat ./time_mcp.pid)
    echo "Found Time MCP server with PID: $TIME_MCP_PID"
    
    # Check if the process is still running
    if ps -p $TIME_MCP_PID > /dev/null; then
        echo "Stopping Time MCP server..."
        kill $TIME_MCP_PID
        
        # Wait for the process to terminate
        sleep 2
        
        # Check if it's still running
        if ps -p $TIME_MCP_PID > /dev/null; then
            echo "Server did not stop gracefully. Forcing termination..."
            kill -9 $TIME_MCP_PID
        fi
        
        echo "Time MCP server stopped."
    else
        echo "Time MCP server is not running with PID: $TIME_MCP_PID"
    fi
    
    # Remove PID file
    rm ./time_mcp.pid
    echo "Removed PID file."
else
    echo "No Time MCP server PID file found. The server might not be running."
fi