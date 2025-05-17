# Database and Storage

This section provides comprehensive documentation related to TripSage's data persistence layer, covering its architecture, setup, specific database technologies, and implementation details.

## Overview

TripSage employs a **dual-storage architecture** to optimally handle different types of data and query patterns. This strategy combines the strengths of relational databases for structured data and graph databases for complex relationships and semantic knowledge.

1. **Relational Database (SQL)**:

    - **Technology**: PostgreSQL.
    - **Providers**:
      - **Supabase**: Used for production and staging environments. Provides managed PostgreSQL along with integrated services like authentication, real-time capabilities, and storage.
      - **Neon**: Used for development and testing environments. Offers serverless PostgreSQL with excellent branching capabilities, allowing for isolated databases per feature or developer.
    - **Purpose**: Stores core structured data such as user accounts, trip itineraries, booking details, and other transactional information.

2. **Knowledge Graph Database (Graph)**:

    - **Technology**: Neo4j.
    - **Integration**: Accessed via the official **Memory MCP (Model Context Protocol) Server**.
    - **Purpose**: Stores relationship-rich data, including travel entity connections (destinations, accommodations, flights), user preferences, historical travel patterns, and semantic knowledge that powers AI agent recommendations and contextual understanding.

3. **Caching Layer**:
    - **Technology**: Redis.
    - **Purpose**: Used for caching frequently accessed data, API responses, and search results to improve performance and reduce load on primary data stores and external APIs. Details are covered in the [Search and Caching](../05_SEARCH_AND_CACHING/README.md) section.

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
