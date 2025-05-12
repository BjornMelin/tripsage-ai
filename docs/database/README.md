# Database Documentation

This directory contains documentation related to TripSage's database architecture, setup, and implementation details.

## Contents

- `database_setup.md` - General database setup instructions
- `db_updates.md` - Database update and migration procedures
- `neo4j_knowledge_graph.md` - Comprehensive guide to Neo4j knowledge graph implementation
- `supabase_integration.md` - Supabase integration details

## Database Architecture

TripSage uses a dual-storage architecture:

1. **Supabase (PostgreSQL)** - Primary database for structured data

   - User accounts and profiles
   - Trip details and itineraries
   - Booking information
   - Structured travel data

2. **Neo4j Knowledge Graph** - Secondary database for relationship-focused data
   - Travel entity relationships
   - Complex travel patterns
   - Domain knowledge representation
   - Semantic relationships

## Key Files

- `neo4j_knowledge_graph.md` - Comprehensive single document covering all Neo4j implementation details
- `supabase_integration.md` - Detailed guide for Supabase integration

## Legacy Files

The following files have been consolidated into `neo4j_knowledge_graph.md`:

- `neo4j_implementation.md`
- `neo4j_implementation_guide.md`
- `neo4j_implementation_plan.md`
