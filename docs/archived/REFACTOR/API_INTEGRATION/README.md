# API Integration Refactoring Documentation

## Overview

This directory contains comprehensive research and planning documentation for
migrating TripSage from MCP (Model Context Protocol) server wrappers to direct
API/SDK integration.

## Documents

### 1. [MCP_TO_SDK_MIGRATION_RESEARCH.md](./MCP_TO_SDK_MIGRATION_RESEARCH.md)

**Purpose**: Comprehensive analysis comparing MCP server wrappers vs direct SDK
integration for all 12 external services used by TripSage.

**Key Contents**:

- Current MCP architecture analysis (323 lines in manager.py, 470 lines in settings)
- Service-by-service evaluation matrix with 7 criteria scored 1-5
- Performance, maintainability, and developer experience comparisons
- Research methodology using Context7, Firecrawl, Exa, Tavily, and Sequential
  Thinking tools
- Final recommendations for each service

**Key Finding**: After cross-analysis with crawling and database research, 11 of 12
services should migrate to direct SDK integration (only Airbnb remains MCP).
Expected 50-70% latency reduction and 3000+ lines code reduction.

### 2. [MCP_TO_SDK_MIGRATION_PLAN.md](./MCP_TO_SDK_MIGRATION_PLAN.md)

**Purpose**: Detailed implementation plan with code examples, timelines, and
rollback strategies for migrating from MCP to direct SDKs.

**Key Contents**:

- Phase-by-phase migration plan across 3 sprints (23-34 development days)
- Complete code examples for Redis, Supabase, and Neo4j migrations
- Feature flag system for zero-downtime deployment
- Performance testing and validation strategies
- Monitoring, alerting, and rollback procedures

**Implementation Priority**:

- **Tier 1 (HIGH)**: Redis, Supabase, Neo4j - immediate 30-50% latency reduction
- **Tier 2 (MEDIUM)**: Time, Duffel Flights, Google Calendar, Google Maps, Crawl4AI, Playwright
- **Tier 3 (LOW)**: Weather
- **Deprecated**: Firecrawl (replaced by Crawl4AI)
- **Keep MCP**: Airbnb only

## Quick Reference

### Final Architecture (Post All Research)

**Service Count Evolution**:

- Original: 12 services (all MCP)
- After API research: 8 direct SDK, 4 MCP
- After DB research: Eliminated Neon, Qdrant, Neo4j for MVP
- After crawling research: Eliminated Firecrawl
- **Final: 8 total services (7 direct SDK, 1 MCP)**

### Services to Migrate (7/8)

| Service             | Current Lines | After Migration | Priority | Expected Benefit                       |
| ------------------- | ------------- | --------------- | -------- | -------------------------------------- |
| **DragonflyDB**     | 394 (Redis)   | ~50             | HIGH     | 25x performance, drop-in Redis replacement |
| **Supabase**        | 139           | ~20             | HIGH     | 30-40% faster, includes pgvector       |
| **Google Maps**     | ~150          | ~60             | MEDIUM   | Full Maps Platform access              |
| **Time**            | ~80           | ~20             | MEDIUM   | Network → Local computation            |
| **Duffel Flights**  | ~120          | ~40             | MEDIUM   | Full API access                        |
| **Google Calendar** | ~110          | ~50             | MEDIUM   | Official client reliability            |
| **Weather**         | ~100          | ~30             | LOW      | Simple HTTP client                     |

### New Direct SDK Services

| Service        | Purpose                           | Benefit                            |
| -------------- | --------------------------------- | ---------------------------------- |
| **Crawl4AI**   | Primary web crawling (85% cases)  | 6x faster than Firecrawl          |
| **Playwright** | Complex JS sites (15% cases)      | 25-40% faster than MCP wrapper    |
| **Mem0**       | AI memory management              | 91% lower latency, 26% better accuracy |

### Services to Keep MCP (1/8)

| Service    | Reason to Keep MCP                   |
| ---------- | ------------------------------------ |
| **Airbnb** | Unofficial API complexity management |

### Deprecated Services

| Service      | Replacement        | Savings                |
| ------------ | ------------------ | ---------------------- |
| **Firecrawl** | Crawl4AI          | $700-1200/year        |
| **Neon DB**   | Supabase          | $500-800/month        |
| **Qdrant**    | pgvector          | 11x performance gain  |
| **Neo4j MVP** | Mem0 (defer to v2) | 60-70% complexity reduction |
| **Redis**     | DragonflyDB       | 25x performance, 80% cost savings |

## Migration Timeline

```text
Week 1:    Infrastructure Setup - DragonflyDB, pgvector, Mem0
Week 2:    Core Services - Supabase (with pgvector), Service Registry
Week 3:    Web Crawling - Crawl4AI, Playwright direct SDK
Week 4:    API Services - Maps, Calendar, Flights, Time, Weather
Week 5-6:  Testing, Performance Validation, Optimization
Week 7-8:  Production Deployment with Feature Flags
```

## Key Benefits

- **Performance**: 50-70% overall latency reduction, 6-10x crawling improvement
- **Maintainability**: ~3000 lines of wrapper code eliminated
- **Developer Experience**: Direct SDK access, unified async patterns
- **Reliability**: Fewer network hops, official client support
- **Cost**: $1,500-2,000/month savings from service consolidation
- **Simplicity**: 8 services instead of 12, single database for MVP

## Next Steps

1. Review and approve migration strategy
2. Allocate development resources (2-3 senior developers)
3. Set up feature flag infrastructure
4. Begin with Tier 1 migrations (Redis, Supabase, Neo4j)
5. Monitor performance improvements and iterate

## Related Documentation

- [MCP Abstraction Layer](../../../tripsage/mcp_abstraction/) - Current implementation
- [Services Configuration](../../../tripsage/config/mcp_settings.py) - MCP settings
- [API Documentation](../../04_MCP_SERVERS/) - MCP server documentation

---

**Last Updated**: 2025-05-25
