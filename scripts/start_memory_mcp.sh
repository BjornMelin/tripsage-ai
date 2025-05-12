#!/bin/bash

# Start Neo4j Memory MCP server

echo "Starting Neo4j Memory MCP server..."

# Check if mcp-neo4j-memory is installed
if ! pip show mcp-neo4j-memory > /dev/null 2>&1; then
    echo "Installing mcp-neo4j-memory..."
    pip install mcp-neo4j-memory
fi

# Load environment variables
if [ -f .env ]; then
    # Extract Neo4j configuration from .env
    NEO4J_URI=$(grep -o '^NEO4J_URI=.*' .env | cut -d '=' -f2)
    NEO4J_USER=$(grep -o '^NEO4J_USER=.*' .env | cut -d '=' -f2)
    NEO4J_PASSWORD=$(grep -o '^NEO4J_PASSWORD=.*' .env | cut -d '=' -f2)
    NEO4J_DATABASE=$(grep -o '^NEO4J_DATABASE=.*' .env | cut -d '=' -f2)
    MEMORY_MCP_PORT=$(grep -o '^MEMORY_MCP_ENDPOINT=.*' .env | cut -d ':' -f3)
else
    # Default configuration
    NEO4J_URI="bolt://localhost:7687"
    NEO4J_USER="neo4j"
    NEO4J_PASSWORD="tripsage_password"
    NEO4J_DATABASE="neo4j"
    MEMORY_MCP_PORT="3008"
fi

# Start the MCP server with Neo4j configuration
echo "Starting Memory MCP server with Neo4j configuration:"
echo "  URI: $NEO4J_URI"
echo "  User: $NEO4J_USER"
echo "  Database: $NEO4J_DATABASE"
echo "  Port: $MEMORY_MCP_PORT"

export NEO4J_URI=$NEO4J_URI
export NEO4J_USER=$NEO4J_USER
export NEO4J_PASSWORD=$NEO4J_PASSWORD
export NEO4J_DATABASE=$NEO4J_DATABASE

# Start the server
python -m mcp_neo4j_memory --port $MEMORY_MCP_PORT