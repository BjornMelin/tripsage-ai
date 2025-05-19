#!/bin/bash

# Start Neo4j Memory MCP server
# This script starts the Neo4j Memory MCP server using the external mcp-neo4j-memory package
# Usage: ./start_memory_mcp.sh [--debug] [--port PORT]

set -e # Exit immediately if a command exits with a non-zero status

DEBUG=0
CUSTOM_PORT=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --debug)
      DEBUG=1
      shift
      ;;
    --port)
      CUSTOM_PORT="$2"
      shift
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--debug] [--port PORT]"
      exit 1
      ;;
  esac
done

echo "Starting Neo4j Memory MCP server..."

# Check if uv is available and preferred for package installation
if command -v uv &> /dev/null; then
    INSTALL_CMD="uv pip install"
else
    INSTALL_CMD="pip install"
fi

# Check if mcp-neo4j-memory is installed
if ! pip show mcp-neo4j-memory > /dev/null 2>&1; then
    echo "Installing mcp-neo4j-memory..."
    $INSTALL_CMD mcp-neo4j-memory || {
        echo "Error: Failed to install mcp-neo4j-memory package"
        echo "Please install manually with: pip install mcp-neo4j-memory"
        exit 1
    }
fi

# Check if Neo4j is running
function check_neo4j() {
    if command -v nc &> /dev/null; then
        # Try to connect to Neo4j Bolt port
        if ! nc -z localhost 7687 &> /dev/null; then
            echo "Warning: Neo4j may not be running on port 7687"
            echo "Recommended: Start Neo4j with 'docker-compose -f docker-compose-neo4j.yml up -d'"
            return 1
        fi
    fi
    return 0
}

# Load environment variables
if [ -f .env ]; then
    echo "Loading configuration from .env file"
    # Extract Neo4j configuration from .env
    NEO4J_URI=$(grep -o '^NEO4J_URI=.*' .env | cut -d '=' -f2 || echo "bolt://localhost:7687")
    NEO4J_USER=$(grep -o '^NEO4J_USER=.*' .env | cut -d '=' -f2 || echo "neo4j")
    NEO4J_PASSWORD=$(grep -o '^NEO4J_PASSWORD=.*' .env | cut -d '=' -f2 || echo "password")
    NEO4J_DATABASE=$(grep -o '^NEO4J_DATABASE=.*' .env | cut -d '=' -f2 || echo "neo4j")

    if [ -z "$CUSTOM_PORT" ]; then
        # Extract port from MEMORY_MCP_ENDPOINT if available
        if grep -q '^MEMORY_MCP_ENDPOINT=.*' .env; then
            MEMORY_MCP_PORT=$(grep -o '^MEMORY_MCP_ENDPOINT=.*' .env | grep -o ':[0-9]*' | cut -d ':' -f2 || echo "3008")
        else
            echo "Warning: MEMORY_MCP_ENDPOINT not found in .env, using default port 3008"
            MEMORY_MCP_PORT="3008"
        fi
    else
        MEMORY_MCP_PORT="$CUSTOM_PORT"
    fi
else
    echo "Warning: .env file not found, using default configuration"
    # Default configuration
    NEO4J_URI="bolt://localhost:7687"
    NEO4J_USER="neo4j"
    NEO4J_PASSWORD="password"
    NEO4J_DATABASE="neo4j"

    if [ -z "$CUSTOM_PORT" ]; then
        MEMORY_MCP_PORT="3008"
    else
        MEMORY_MCP_PORT="$CUSTOM_PORT"
    fi
fi

# Start the MCP server with Neo4j configuration
echo "Starting Memory MCP server with Neo4j configuration:"
echo "  URI: $NEO4J_URI"
echo "  User: $NEO4J_USER"
echo "  Database: $NEO4J_DATABASE"
echo "  Port: $MEMORY_MCP_PORT"

# Check Neo4j connection
check_neo4j

# Export variables for the Python script
export NEO4J_URI=$NEO4J_URI
export NEO4J_USER=$NEO4J_USER
export NEO4J_PASSWORD=$NEO4J_PASSWORD
export NEO4J_DATABASE=$NEO4J_DATABASE

# Start the server
CMD="python -m mcp_neo4j_memory --port $MEMORY_MCP_PORT"

if [ "$DEBUG" -eq 1 ]; then
    echo "Starting in debug mode..."
    $CMD --log-level debug
else
    echo "Starting in normal mode..."
    $CMD
fi

# Check exit status
if [ $? -ne 0 ]; then
    echo "Error: Failed to start Memory MCP server"
    echo "Please check the logs for more information"
    exit 1
fi