# 🏗️ Database Architecture Diagrams

> **Simplified Database Infrastructure | Performance Optimization | BJO-212**  
> Comprehensive architectural diagrams showcasing the 64.8% code reduction achievement  
> *Last updated: June 17, 2025*

## 📋 Table of Contents

- [High-Level Architecture](#high-level-architecture)
- [Simplified PGVector Service Architecture](#simplified-pgvector-service-architecture)
- [Data Flow for Vector Operations](#data-flow-for-vector-operations)
- [Connection Pooling Architecture](#connection-pooling-architecture)
- [Cache Integration Pattern](#cache-integration-pattern)
- [Memory Service Integration](#memory-service-integration)
- [Monitoring Architecture](#monitoring-architecture)
- [Before vs After Complexity](#before-vs-after-complexity)
- [Performance Optimization Profiles](#performance-optimization-profiles)
- [Deployment Architecture](#deployment-architecture)
- [Key Benefits Visualization](#key-benefits-visualization)

## Overview

This document provides architectural diagrams for the simplified database infrastructure implemented as part of BJO-212 - Database Service Performance Optimization Framework.

## High-Level Architecture

```mermaid
graph TB
    subgraph "Application Layer"
        API[FastAPI Application]
        MEM[Memory Service]
        BUS[Business Services]
    end

    subgraph "Infrastructure Layer"
        PGV[PGVector Service]
        DBM[Database Monitor]
        CACHE[Cache Service]
        WS[WebSocket Services]
    end

    subgraph "Data Layer"
        SUPA[Supabase PostgreSQL<br/>with pgvector]
        DRAG[DragonflyDB Cache]
        POOL[Supavisor<br/>Connection Pooler]
    end

    API --> MEM
    API --> BUS
    MEM --> PGV
    BUS --> PGV
    PGV --> DBM
    PGV --> CACHE
    
    PGV --> POOL
    CACHE --> DRAG
    POOL --> SUPA
    
    WS -.-> CACHE
    WS -.-> SUPA

    style PGV fill:#90EE90
    style POOL fill:#87CEEB
    style DRAG fill:#FFB6C1
```

## Simplified PGVector Service Architecture

```mermaid
classDiagram
    class PGVectorService {
        -db: DatabaseService
        -profiles: Dict[OptimizationProfile, IndexConfig]
        +create_hnsw_index()
        +set_query_quality()
        +get_index_stats()
        +check_index_health()
        +optimize_for_table()
        +optimize_memory_tables()
    }

    class OptimizationProfile {
        <<enumeration>>
        SPEED
        BALANCED
        QUALITY
    }

    class IndexConfig {
        +m: int = 16
        +ef_construction: int = 64
        +ef_search: int = 40
    }

    class IndexStats {
        +index_name: str
        +index_size_bytes: int
        +row_count: int
        +index_usage_count: int
    }

    PGVectorService --> OptimizationProfile
    PGVectorService --> IndexConfig
    PGVectorService --> IndexStats
    PGVectorService --> DatabaseService
```

## Data Flow for Vector Operations

```mermaid
sequenceDiagram
    participant User
    participant API
    participant MemoryService
    participant PGVectorService
    participant Supavisor
    participant PostgreSQL

    User->>API: Search Request
    API->>MemoryService: search_memories()
    MemoryService->>MemoryService: Check Cache
    
    alt Cache Miss
        MemoryService->>PGVectorService: set_query_quality(100)
        PGVectorService->>Supavisor: SET hnsw.ef_search = 100
        Supavisor->>PostgreSQL: Configure Session
        
        MemoryService->>Supavisor: Vector Search Query
        Supavisor->>PostgreSQL: Execute Search
        PostgreSQL-->>Supavisor: Results
        Supavisor-->>MemoryService: Results
        
        MemoryService->>MemoryService: Cache Results
    end
    
    MemoryService-->>API: Search Results
    API-->>User: Response
```

## Connection Pooling Architecture

```mermaid
graph LR
    subgraph "Application Instances"
        APP1[App Instance 1]
        APP2[App Instance 2]
        APP3[App Instance 3]
    end

    subgraph "Supavisor Layer"
        POOL1[Transaction Pool<br/>Port 6543]
        POOL2[Session Pool<br/>Port 5432]
    end

    subgraph "PostgreSQL"
        PG[(PostgreSQL<br/>+ pgvector)]
    end

    APP1 --> POOL1
    APP2 --> POOL1
    APP3 --> POOL1
    
    POOL1 --> PG
    POOL2 --> PG
    
    style POOL1 fill:#87CEEB
    style POOL2 fill:#B0C4DE
```

## Cache Integration Pattern

```mermaid
graph TD
    subgraph "Cache Strategy"
        REQ[Request]
        CHECK{Cache<br/>Check}
        HIT[Cache Hit]
        MISS[Cache Miss]
        
        REQ --> CHECK
        CHECK -->|Found| HIT
        CHECK -->|Not Found| MISS
        
        MISS --> QUERY[Database Query]
        QUERY --> STORE[Store in Cache]
        STORE --> RETURN[Return Result]
        HIT --> RETURN
    end

    subgraph "DragonflyDB Features"
        LRU[LRU Eviction]
        TTL[TTL Expiration]
        PERF[6.4M ops/sec]
    end
    
    CHECK -.-> LRU
    STORE -.-> TTL
    CHECK -.-> PERF
```

## Memory Service Integration

```mermaid
graph TB
    subgraph "Memory Operations"
        CONV[Conversation<br/>Memory]
        PREF[User<br/>Preferences]
        CONT[User<br/>Context]
    end

    subgraph "Memory Service"
        MEM0[Mem0 Library]
        VECOPT[Vector<br/>Optimization]
        CACHE[Result<br/>Cache]
    end

    subgraph "Storage"
        PGVEC[pgvector<br/>Tables]
        DRAG[DragonflyDB]
    end

    CONV --> MEM0
    PREF --> MEM0
    CONT --> MEM0
    
    MEM0 --> VECOPT
    VECOPT --> PGVEC
    
    MEM0 --> CACHE
    CACHE --> DRAG
    
    style VECOPT fill:#90EE90
    style DRAG fill:#FFB6C1
```

## Monitoring Architecture

```mermaid
graph LR
    subgraph "Consolidated Monitor"
        MON[Database Monitor]
        HEALTH[Health Checks]
        PERF[Performance Metrics]
        SEC[Security Events]
    end

    subgraph "Metrics Collection"
        QUERY[Query Stats]
        CONN[Connection Stats]
        INDEX[Index Usage]
    end

    subgraph "Outputs"
        LOG[Structured Logs]
        ALERT[Alerts]
        DASH[Dashboards]
    end

    MON --> HEALTH
    MON --> PERF
    MON --> SEC
    
    HEALTH --> QUERY
    PERF --> CONN
    PERF --> INDEX
    
    QUERY --> LOG
    CONN --> ALERT
    INDEX --> DASH
    
    style MON fill:#FFA07A
```

## Before vs After Complexity

```mermaid
graph TD
    subgraph "Before: Complex Architecture"
        OLD_API[API Layer]
        OLD_ABS1[Abstraction Layer 1]
        OLD_ABS2[Abstraction Layer 2]
        OLD_POOL[Custom Pool Manager]
        OLD_MON1[Query Monitor]
        OLD_MON2[Health Monitor]
        OLD_MON3[Perf Monitor]
        OLD_OPT[PGVector Optimizer<br/>1,311 lines]
        OLD_CACHE1[Cache Layer 1]
        OLD_CACHE2[Cache Layer 2]
        OLD_DB[(Database)]
        
        OLD_API --> OLD_ABS1
        OLD_ABS1 --> OLD_ABS2
        OLD_ABS2 --> OLD_POOL
        OLD_POOL --> OLD_OPT
        OLD_OPT --> OLD_DB
        OLD_MON1 --> OLD_OPT
        OLD_MON2 --> OLD_OPT
        OLD_MON3 --> OLD_OPT
        OLD_CACHE1 --> OLD_CACHE2
        OLD_CACHE2 --> OLD_DB
    end

    subgraph "After: Simplified Architecture"
        NEW_API[API Layer]
        NEW_SVC[PGVector Service<br/>462 lines]
        NEW_MON[Consolidated Monitor]
        NEW_POOL[Supavisor]
        NEW_DB[(Database)]
        
        NEW_API --> NEW_SVC
        NEW_SVC --> NEW_POOL
        NEW_POOL --> NEW_DB
        NEW_MON -.-> NEW_SVC
    end
    
    style OLD_OPT fill:#FF6B6B
    style NEW_SVC fill:#90EE90
```

## Performance Optimization Profiles

```mermaid
graph TD
    subgraph "Optimization Profiles"
        SPEED[Speed Profile<br/>m=16, ef=64/40]
        BALANCED[Balanced Profile<br/>m=16, ef=64/100]
        QUALITY[Quality Profile<br/>m=16, ef=100/200]
    end

    subgraph "Use Cases"
        REALTIME[Real-time Search<br/><10ms latency]
        STANDARD[Standard Search<br/><50ms latency]
        ACCURACY[High Accuracy<br/><100ms latency]
    end

    SPEED --> REALTIME
    BALANCED --> STANDARD
    QUALITY --> ACCURACY
    
    style SPEED fill:#90EE90
    style BALANCED fill:#FFD700
    style QUALITY fill:#87CEEB
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Development"
        DEV[Local PostgreSQL<br/>+ pgvector]
    end

    subgraph "Staging"
        STAGE_APP[Application]
        STAGE_SUPA[Supabase Staging]
        STAGE_DRAG[DragonflyDB]
    end

    subgraph "Production"
        PROD_LB[Load Balancer]
        PROD_APP1[App Instance 1]
        PROD_APP2[App Instance 2]
        PROD_SUPA[Supabase Production<br/>with Supavisor]
        PROD_DRAG[DragonflyDB Cluster]
    end

    DEV --> STAGE_APP
    STAGE_APP --> STAGE_SUPA
    STAGE_APP --> STAGE_DRAG
    
    PROD_LB --> PROD_APP1
    PROD_LB --> PROD_APP2
    PROD_APP1 --> PROD_SUPA
    PROD_APP2 --> PROD_SUPA
    PROD_APP1 --> PROD_DRAG
    PROD_APP2 --> PROD_DRAG
    
    style PROD_SUPA fill:#90EE90
    style PROD_DRAG fill:#FFB6C1
```

## Key Benefits Visualization

```mermaid
pie title Code Reduction by Component
    "Removed Code" : 65
    "Simplified Code" : 25
    "New Clean Code" : 10
```

```mermaid
graph LR
    subgraph "Performance Gains"
        OLD_LAT[20ms Latency] --> NEW_LAT[<10ms Latency]
        OLD_MEM[High Memory] --> NEW_MEM[30% Less Memory]
        OLD_CONN[Complex Pooling] --> NEW_CONN[Native Pooling]
    end
    
    style NEW_LAT fill:#90EE90
    style NEW_MEM fill:#90EE90
    style NEW_CONN fill:#90EE90
```

---

## Next Steps

- [PGVector Monitoring Guide](/docs/operators/pgvector-monitoring-guide.md) - Set up production monitoring
- [Database Optimization Lessons](/docs/developers/database-optimization-lessons.md) - Learn from our optimization journey
- [Performance Optimization Guide](/docs/developers/performance-optimization.md) - General performance best practices

---

*Architecture diagrams created: June 17, 2025*  
*Project: BJO-212 - Database Service Performance Optimization Framework*