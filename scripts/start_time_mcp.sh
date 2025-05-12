#!/bin/bash
# Deployment script for the Time MCP server
# This script will install and run the official Time MCP server from the Model Context Protocol

# Exit immediately on error
set -e

echo "Starting Time MCP server deployment..."

# Check if uvx is installed (using uv command for checking)
if ! command -v uv &> /dev/null; then
    echo "uv/uvx is not installed. Installing now..."
    curl -fsSL https://astral.sh/uv/install.sh | sh
    echo "uv/uvx installed successfully."
fi

# Determine local timezone
LOCAL_TZ=$(date +%Z)
echo "Detected local timezone: $LOCAL_TZ"

# Set up port (default to 8004 which is the standard for Time MCP)
PORT=${TIME_MCP_PORT:-8004}
echo "Time MCP server will run on port: $PORT"

# Log file location
LOG_DIR="./logs"
mkdir -p $LOG_DIR
LOG_FILE="$LOG_DIR/time_mcp_$(date +%Y%m%d_%H%M%S).log"

echo "Starting Time MCP server..."
echo "Logs will be written to: $LOG_FILE"

# Start the MCP server using uvx to run the mcp-server-time package
# This will automatically download and run the package without needing to install it
nohup uvx mcp-server-time --local-timezone=$LOCAL_TZ > $LOG_FILE 2>&1 &
SERVER_PID=$!

# Wait a bit to make sure the server started correctly
sleep 2

# Check if the server is running
if ps -p $SERVER_PID > /dev/null; then
    echo "Time MCP server started successfully with PID: $SERVER_PID"
    echo $SERVER_PID > ./time_mcp.pid
    echo "PID saved to ./time_mcp.pid"
    echo "To stop the server, run: kill $(cat ./time_mcp.pid)"
    echo "Server is running on http://localhost:$PORT"
else
    echo "Failed to start Time MCP server. Check the log file for details: $LOG_FILE"
    exit 1
fi

# Add configuration instructions
echo ""
echo "Configuration Instructions:"
echo "--------------------------"
echo "To configure TripSage to use this Time MCP server:"
echo "1. Add the following to your .env file:"
echo "   TIME_MCP_SERVER_URL=http://localhost:$PORT"
echo ""
echo "2. If you need to debug or test the server, you can use the MCP inspector:"
echo "   npx @modelcontextprotocol/inspector uvx mcp-server-time"
echo ""