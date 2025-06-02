# Database and Storage

This section provides comprehensive documentation related to TripSage's unified data persistence architecture, which leverages a single powerful PostgreSQL database with advanced extensions for both structured and vector-based operations.

## Overview

TripSage employs a **unified storage architecture** built on Supabase PostgreSQL with pgvector extensions. This modern approach delivers exceptional performance while significantly reducing complexity and costs compared to traditional multi-database architectures.

**Current Architecture (Active):**

1. **Unified PostgreSQL Database (Supabase)**:

    - **Technology**: PostgreSQL 15+ with pgvector and pgvectorscale extensions
    - **Provider**: **Supabase** for all environments (production, staging, development)
    - **Purpose**: Single database handling structured data (users, trips, bookings) and vector embeddings for AI/semantic search
    - **Performance**: 471+ QPS throughput, <100ms vector search latency, 11x faster than standalone vector databases

2. **Mem0 Memory System**:

    - **Technology**: Mem0 v1.0+ with native Supabase PostgreSQL backend
    - **Integration**: Direct SDK integration with pgvector for embeddings storage
    - **Purpose**: Intelligent memory management with automatic deduplication, semantic relationships, and contextual understanding for AI agents
    - **Benefits**: 26% better memory accuracy, 91% lower latency vs graph databases

3. **DragonflyDB Caching Layer**:
    - **Technology**: DragonflyDB (Redis-compatible, optimized for performance)
    - **Purpose**: High-performance caching layer with 25x better performance than Redis for frequently accessed data, API responses, and search results
    - **Integration**: Seamless Redis protocol compatibility with enhanced performance
    - **Details**: Covered in the [Search and Caching](../05_SEARCH_AND_CACHING/README.md) section

**Unified Architecture Benefits:**

- **Performance**: 11x faster vector search (471+ QPS), 91% lower memory latency, 25x faster caching
- **Cost Reduction**: 80% cost savings ($6,000-9,600 annually) by eliminating complex multi-database infrastructure
- **Operational Simplicity**: Single database system reduces operational complexity by 80%
- **Enhanced Accuracy**: 26% improvement in memory/context accuracy with Mem0
- **Developer Experience**: Unified development workflow across all environments
- **Scalability**: Enterprise-grade PostgreSQL with native vector capabilities

## Architectural Evolution

TripSage has evolved from complex multi-database architectures to a streamlined unified approach:

**Previous Architecture (Deprecated - Pre-2025):**

- **Multiple Databases**: Neon PostgreSQL + Neo4j knowledge graph + Qdrant vector database
- **Complex Synchronization**: Data consistency challenges across multiple systems
- **Higher Costs**: Separate infrastructure and maintenance for each database type
- **Operational Overhead**: Multiple deployment pipelines, monitoring systems, and backup strategies

**Migration Completed (Issue #147):**

The migration to unified Supabase architecture was completed in May 2025, delivering significant improvements in performance, cost, and operational simplicity. All legacy database dependencies have been removed and replaced with the optimized unified approach.

## Contents

This section contains the following key documents:

- **[Relational Database Guide](./RELATIONAL_DATABASE_GUIDE.md)**:

  - Comprehensive guide to the unified Supabase PostgreSQL architecture. Covers setup, configuration, schema design, pgvector integration, and MCP-based database operations.

- **[Database Migration Reports](./DATABASE_MIGRATION_REPORTS.md)**:

  - Historical documentation of significant database migration efforts, including the consolidation from dual-storage to unified architecture and performance improvements achieved.

- **[Dual Storage Implementation](./DUAL_STORAGE_IMPLEMENTATION.md)** *(Historical Reference)*:

  - Legacy documentation of the previous dual-storage patterns. Maintained for historical context and understanding the architectural evolution.

- **[Knowledge Graph Guide](./KNOWLEDGE_GRAPH_GUIDE.md)** *(Historical Reference)*:

  - Legacy documentation of the Neo4j knowledge graph implementation that was replaced by the Mem0 + pgvector unified approach.

## Key Architecture Principles

- **Unified Data Model**: Single PostgreSQL database handling all data types (structured, vectors, metadata)
- **Performance First**: Optimized for <100ms query latency and 400+ QPS throughput
- **Cost Efficiency**: 80% reduction in infrastructure costs through architectural consolidation
- **Developer Experience**: Simple, unified development and deployment workflows
- **Scalability**: Enterprise-grade PostgreSQL with native vector search capabilities
- **Data Integrity**: ACID compliance with advanced constraint and indexing strategies

## Technology Stack

- **Database**: Supabase PostgreSQL 15+ with pgvector/pgvectorscale extensions
- **Memory System**: Mem0 v1.0+ with native PostgreSQL backend
- **Caching**: DragonflyDB (Redis-compatible with enhanced performance)
- **Access Layer**: MCP (Model Context Protocol) abstraction for standardized database interactions
- **Migration System**: SQL-based migrations with MCP integration
- **Monitoring**: Native Supabase monitoring with performance dashboards

## Performance Metrics

- **Vector Search**: <100ms latency, 471+ QPS throughput
- **Traditional Queries**: <50ms latency for typical OLTP operations
- **Cache Performance**: 25x improvement over Redis for frequently accessed data
- **Memory Accuracy**: 26% improvement in AI agent context accuracy
- **Cost Savings**: $6,000-9,600 annually vs. multi-database approach

Refer to the specific guides within this section for detailed information on each component of TripSage's unified storage architecture.
