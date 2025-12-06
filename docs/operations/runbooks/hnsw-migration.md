# HNSW Migration Playbook (pgvector)

Operational steps to migrate IVFFlat indexes to HNSW for `accommodation_embeddings` and `memories.turn_embeddings` without downtime.

## Scope

- Tables: `public.accommodation_embeddings`, `memories.turn_embeddings` (1536-d vectors, L2).
- Target params: `m=32`, `ef_construction=180` (160 if RAM constrained), default `hnsw.ef_search=96` (tune 64–128 per query).

## Preconditions

- pgvector extension ≥ 0.5.0 installed.
- Sufficient RAM for concurrent HNSW build (estimate 1–1.5x index size during build).
- Monitor `pg_stat_activity` and `pg_stat_user_indexes` access patterns to pick a low-traffic window.

## Migration steps

1) **Create new HNSW indexes concurrently** (keep IVFFlat online):

```sql
-- accommodations
CREATE INDEX CONCURRENTLY IF NOT EXISTS accommodation_embeddings_embedding_hnsw_idx
  ON public.accommodation_embeddings
  USING hnsw (embedding vector_l2_ops) WITH (m = 32, ef_construction = 180);

-- memories
CREATE INDEX CONCURRENTLY IF NOT EXISTS memories_turn_embeddings_vector_hnsw_idx
  ON memories.turn_embeddings
  USING hnsw (embedding vector_l2_ops) WITH (m = 32, ef_construction = 180);
```

2) **Set per-query defaults** in functions/queries:

```sql
PERFORM set_config('hnsw.ef_search', '96', true); -- adjust 64–128 if needed
```

3) **Validate**

- Compare recall/latency vs IVFFlat on a sampled workload.
- Check index usage: `SELECT * FROM pg_stat_user_indexes WHERE indexrelname LIKE '%embedding%';`
- Confirm row estimates look sane: `ANALYZE` tables after build.

4) **Cutover**

- Update application/query functions to rely on HNSW (already done in `match_accommodation_embeddings`).
- Keep IVFFlat for one validation window; then drop to reclaim disk:

```sql
DROP INDEX CONCURRENTLY IF EXISTS accommodation_embeddings_embedding_idx; -- old IVFFlat name
ALTER INDEX accommodation_embeddings_embedding_hnsw_idx RENAME TO accommodation_embeddings_embedding_idx;

DROP INDEX CONCURRENTLY IF EXISTS memories_turn_embeddings_vector_idx; -- old IVFFlat name
ALTER INDEX memories_turn_embeddings_vector_hnsw_idx RENAME TO memories_turn_embeddings_vector_idx;
```

5) **Rollback**

- If HNSW regression is detected, drop the HNSW index and keep IVFFlat:

```sql
DROP INDEX CONCURRENTLY IF EXISTS accommodation_embeddings_embedding_hnsw_idx;
DROP INDEX CONCURRENTLY IF EXISTS memories_turn_embeddings_vector_hnsw_idx;
```

## Monitoring

- Track query latency and buffer/cache hit rates before/after cutover.
- Watch memory during build (`pg_stat_activity`, system metrics) to avoid OOM.
- Alert if `hnsw.ef_search` drifts from expected defaults (pg_settings).

## Notes

- Write-heavy workloads may still prefer IVFFlat; if so, keep IVFFlat with `lists≈500–1000`, `probes≈20` and skip cutover for the affected table.
- Always run `ANALYZE` after index build/drop to refresh planner stats.
