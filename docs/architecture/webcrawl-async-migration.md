# WebCrawl Async Migration Overview

## Current Pipeline Inventory

- **Crawler**: `tripsage.tools.webcrawl.crawl4ai_client.Crawl4AIClient`
  - Entry points: `scrape_url`, `crawl_blog`, `scrape_with_memory_extraction`
  - Async behaviour: returns `CrawlResult` synchronously today, wraps optional streaming generator by buffering into a list.
- **Parser/Normalizer**: `tripsage.tools.webcrawl.result_normalizer.ResultNormalizer`
  - Async behaviour: pure CPU-bound transformations, invoked synchronously from callers.
- **Persistence**: `tripsage.tools.webcrawl.persistence.WebCrawlPersistence`
  - Async behaviour: external effects (Supabase insert, Mem0 memory storage) already declared async but some helpers call sync wrappers (`add_conversation_memory`).
- **Memory Service**: `tripsage_core.services.business.memory_service.MemoryService`
  - Native async API with `await connect()` and `await add_conversation_memory()`; current client code sometimes assumes synchronous lifecycle.

## Async Migration Objectives

1. **Adopt async-first lifecycle**
   - Initialize shared browser configuration and memory service at app startup (FastAPI lifespan or background worker bootstrap).
   - Remove synchronous shims such as `connect_sync` and event-loop blocking helpers.
2. **Preserve streaming semantics**
   - Propagate async iterators from `AsyncWebCrawler` through higher level APIs instead of buffering into lists.
   - Provide helper utilities for consumers needing eager materialization (`await gather_results(iterator)`).
3. **Align persistence and memory usage**
   - Ensure persistence functions await memory operations directly.
   - Replace mixed sync/async pathways with consistent awaitable interfaces.
4. **Introduce concurrency controls and observability**
   - Define semaphores or dispatchers for crawl concurrency, rate limiting, and cancellation handling.
   - Standardize structured logging/tracing contexts to maintain visibility across async tasks.
5. **Maintain compatibility**
   - Offer thin synchronous facades for legacy callers that run async code under the hood without keeping duplicated logic.

## Planned Phases

- **Phase 1 – Foundations**
  - Complete pipeline inventory (this document).
  - Implement async resource manager and startup/shutdown hooks.
  - Add concurrency governance and cancellation semantics.
  - Enhance observability instrumentation.
- **Phase 2 – Async Core Refactor**
  - Convert Crawl4AI client to async-only API with explicit streaming support.
  - Refactor persistence to await memory service directly.
  - Update unit tests and type hints to reflect async contracts.
- **Phase 3 – Compatibility & Rollout**
  - Ship synchronous compatibility facade.
  - Update documentation and migration guides.
  - Run full linting, typing, and testing suites ensuring no legacy code paths remain.

## Open Questions

- Supabase client current usage: confirm availability of async driver or plan executor-based shim.
- Downstream call sites requiring sync adapters: enumerate consumers after refactor to scope adapter surface.
- Required metrics/alerts for streaming throughput and crawl cancellation outcomes.
