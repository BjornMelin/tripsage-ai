#!/bin/bash

# Setup script for Neo4j database and Neo4j Memory MCP

# Stop on errors
set -e

echo "Setting up Neo4j database and Neo4j Memory MCP for TripSage..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Start Neo4j container
echo "Starting Neo4j container..."
docker-compose -f docker-compose-neo4j.yml up -d

# Wait for Neo4j to be ready
echo "Waiting for Neo4j to be ready..."
for i in {1..30}; do
    if docker exec tripsage-neo4j neo4j status | grep -q "Neo4j is running"; then
        echo "Neo4j is ready!"
        break
    fi
    echo "Waiting for Neo4j to start (attempt $i/30)..."
    sleep 2
done

# Install Neo4j Memory MCP
echo "Installing Neo4j Memory MCP..."
pip install mcp-neo4j-memory

# Update .env file with Neo4j credentials
if [ -f .env ]; then
    echo "Updating .env file with Neo4j credentials..."
    # Backup existing .env file
    cp .env .env.bak
    # Update Neo4j credentials
    sed -i 's/^NEO4J_URI=.*/NEO4J_URI=bolt:\/\/localhost:7687/' .env
    sed -i 's/^NEO4J_USER=.*/NEO4J_USER=neo4j/' .env
    sed -i 's/^NEO4J_PASSWORD=.*/NEO4J_PASSWORD=tripsage_password/' .env
    sed -i 's/^NEO4J_DATABASE=.*/NEO4J_DATABASE=neo4j/' .env
    sed -i 's/^MEMORY_MCP_ENDPOINT=.*/MEMORY_MCP_ENDPOINT=http:\/\/localhost:3008/' .env
else
    echo "Creating .env file with Neo4j credentials..."
    cp .env.example .env
    sed -i 's/^NEO4J_URI=.*/NEO4J_URI=bolt:\/\/localhost:7687/' .env
    sed -i 's/^NEO4J_USER=.*/NEO4J_USER=neo4j/' .env
    sed -i 's/^NEO4J_PASSWORD=.*/NEO4J_PASSWORD=tripsage_password/' .env
    sed -i 's/^NEO4J_DATABASE=.*/NEO4J_DATABASE=neo4j/' .env
    sed -i 's/^MEMORY_MCP_ENDPOINT=.*/MEMORY_MCP_ENDPOINT=http:\/\/localhost:3008/' .env
fi

echo "Setup completed successfully!"
echo "Neo4j is available at: http://localhost:7474/browser/"
echo "Neo4j Bolt URL: bolt://localhost:7687"
echo "Neo4j credentials: neo4j/tripsage_password"
echo "Neo4j Memory MCP endpoint: http://localhost:3008"

echo "To start the Neo4j Memory MCP server, run: python -m mcp_neo4j_memory --port 3008"