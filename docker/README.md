# Docker Configuration

This directory contains Docker compose files for TripSage AI services.

## Files

- `docker-compose.mcp.yml` - MCP (Model Context Protocol) services configuration
- `docker-compose-neo4j.yml` - **DEPRECATED** - Historical Neo4j configuration (system migrated to Mem0)

## Current Architecture

TripSage now uses a unified storage architecture:

- **Database**: Supabase PostgreSQL with pgvector extensions (replaces Neo4j + separate vector database)
- **Memory**: Mem0 direct SDK integration (replaces Neo4j memory MCP)
- **Caching**: DragonflyDB service (Redis-compatible, 25x performance improvement)

## Usage

From the project root:

```bash
# Start MCP services (if needed for development)
docker-compose -f docker/docker-compose.mcp.yml up -d

# Neo4j is no longer needed - system uses Supabase + Mem0
# docker-compose -f docker/docker-compose-neo4j.yml up -d  # DEPRECATED
```

## Migration Notes

- **Neo4j → Mem0**: Knowledge graph functionality migrated to Mem0 with pgvector backend
- **Vector Search**: Now handled by pgvector extensions in Supabase (11x performance improvement)
- **Development**: No local Neo4j instance needed - unified Supabase for all environments
