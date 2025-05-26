# Docker Configuration

This directory contains Docker compose files for TripSage AI services.

## Files

- `docker-compose-neo4j.yml` - Neo4j graph database configuration
- `docker-compose.mcp.yml` - MCP (Model Context Protocol) services configuration

## Usage

From the project root:

```bash
# Start Neo4j
docker-compose -f docker/docker-compose-neo4j.yml up -d

# Start MCP services
docker-compose -f docker/docker-compose.mcp.yml up -d
```