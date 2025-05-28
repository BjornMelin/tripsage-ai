# Database and Storage

This section provides comprehensive documentation related to TripSage's data persistence layer, covering its architecture, setup, specific database technologies, and implementation details.

## Overview

TripSage employs a **unified storage architecture** that optimally handles different types of data and query patterns within a single, powerful database system. This strategy leverages the full capabilities of PostgreSQL with extensions for both structured and semantic data.

**Current Architecture (Active):**

1. **Unified Database (PostgreSQL with Extensions)**:

    - **Technology**: PostgreSQL with pgvector and pgvectorscale extensions.
    - **Provider**: **Supabase** for all environments (production, staging, development).
    - **Purpose**: Stores both structured data (user accounts, trip itineraries, booking details) and vector embeddings for semantic search within the same database instance.
    - **Performance**: Delivers 11x better vector search performance than standalone solutions like Qdrant, with <100ms query latency.

2. **Memory Management System**:

    - **Technology**: Mem0 with pgvector backend.
    - **Integration**: Direct SDK integration for optimal performance.
    - **Purpose**: Provides intelligent memory management with automatic deduplication, semantic relationships, and contextual understanding for AI agents.
    - **Benefits**: 26% better memory accuracy, 91% lower latency compared to Neo4j-based approaches.

3. **Caching Layer**:
    - **Technology**: DragonflyDB (Redis-compatible).
    - **Purpose**: High-performance caching with 25x better performance than Redis for frequently accessed data, API responses, and search results.
    - **Details**: Covered in the [Search and Caching](../05_SEARCH_AND_CACHING/README.md) section.

**Migration Benefits Achieved:**

- **Performance**: 11x faster vector search, 91% lower latency, 25x faster caching
- **Cost Savings**: $6,000-9,600 annually by eliminating dual database infrastructure  
- **Simplified Operations**: 80% reduction in infrastructure complexity
- **Enhanced Accuracy**: 26% better memory accuracy with Mem0
- **Unified Development**: Single database system for all environments

## Previous Architecture (Deprecated)

TripSage previously considered a **dual-storage architecture** combining relational and graph databases:

- **Relational Database**: PostgreSQL via Supabase/Neon for structured data
- **Knowledge Graph**: Neo4j for relationship-rich data and semantic knowledge
- **Vector Database**: Qdrant for semantic search capabilities

This approach was deprecated in favor of the unified architecture following comprehensive research showing significant performance and cost advantages of the pgvector + Mem0 approach.

## Contents

This section contains the following key documents:

- **[Relational Database Guide](./RELATIONAL_DATABASE_GUIDE.md)**:

  - Detailed information on setting up, configuring, and interacting with the PostgreSQL databases (Supabase and Neon). Includes schema migration strategies and MCP integration for database operations.

- **[Knowledge Graph Guide](./KNOWLEDGE_GRAPH_GUIDE.md)**:

  - A comprehensive guide to TripSage's Neo4j knowledge graph implementation. Covers schema design, data modeling, Memory MCP integration, and query patterns.

- **[Dual Storage Implementation](./DUAL_STORAGE_IMPLEMENTATION.md)**:

  - Explains the patterns and services used to manage data consistency and interaction between the relational database and the knowledge graph. Details the refactoring to a service-based architecture.

- **[Database Migration Reports](./DATABASE_MIGRATION_REPORTS.md)**:
  - Historical reports and summaries of significant database migration efforts, such as the move from direct database access to an MCP-based approach.

## Key Principles

- **Data Integrity**: Ensuring accuracy and consistency across both storage systems.
- **Scalability**: Designing schemas and choosing technologies that can scale with user growth and data volume.
- **Performance**: Optimizing queries and data access patterns for fast response times.
- **Flexibility**: Allowing for the evolution of data models as TripSage features expand.
- **Abstraction**: Interacting with databases primarily through MCPs or a dedicated data access layer to decouple business logic from specific database technologies.

Refer to the specific guides within this section for detailed information on each component of TripSage's data storage strategy.
