-- TripSage RAG Documents Schema
-- Generated: 2025-12-11
-- SPEC-0018: RAG Retriever/Indexer

-- NOTE: Supabase CLI can restore `supabase_migrations.schema_migrations` from a cached local backup.
-- If the tracking row for this migration already exists, the CLI will fail at the end when recording
-- the migration version. Make the migration idempotent by deleting any pre-existing row (when present).
DO $do$
BEGIN
  IF to_regclass('supabase_migrations.schema_migrations') IS NOT NULL THEN
    DELETE FROM supabase_migrations.schema_migrations WHERE version = '20251211000000';
  END IF;
END;
$do$;

-- ===========================
-- RAG DOCUMENTS TABLE
-- ===========================

-- Generic RAG document store with pgvector embeddings
CREATE TABLE IF NOT EXISTS public.rag_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  embedding vector(1536),
  metadata JSONB DEFAULT '{}',
  namespace TEXT NOT NULL DEFAULT 'default' CHECK (namespace IN ('default', 'accommodations', 'destinations', 'activities', 'travel_tips', 'user_content')),
  source_id TEXT,
  chunk_index INT DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Unique constraint for document chunks (allows upsert on id + chunk_index)
CREATE UNIQUE INDEX IF NOT EXISTS rag_documents_id_chunk_idx
  ON public.rag_documents (id, chunk_index);

-- HNSW index for fast cosine similarity search
-- m=32 provides good recall/speed balance
-- ef_construction=180 for high quality index
DO $$
DECLARE
  v_hnsw_m integer := COALESCE(NULLIF(current_setting('PGVECTOR_HNSW_M', true), '')::integer, 32);
  v_hnsw_ef_construction integer := COALESCE(
    NULLIF(current_setting('PGVECTOR_HNSW_EF_CONSTRUCTION', true), '')::integer,
    180
  );
BEGIN
  EXECUTE format(
    'CREATE INDEX IF NOT EXISTS rag_documents_embedding_idx ON public.rag_documents USING hnsw (embedding vector_cosine_ops) WITH (m = %s, ef_construction = %s);',
    v_hnsw_m,
    v_hnsw_ef_construction
  );
END;
$$;

-- Namespace index for filtered queries
CREATE INDEX IF NOT EXISTS rag_documents_namespace_idx
  ON public.rag_documents(namespace);

-- Source ID index for document lineage tracking
CREATE INDEX IF NOT EXISTS rag_documents_source_id_idx
  ON public.rag_documents(source_id)
  WHERE source_id IS NOT NULL;

-- Created at index for recency sorting
CREATE INDEX IF NOT EXISTS rag_documents_created_at_idx
  ON public.rag_documents(created_at DESC);

-- Full-text search tsvector column (generated)
ALTER TABLE public.rag_documents
ADD COLUMN IF NOT EXISTS fts tsvector
GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

-- GIN index for full-text search
CREATE INDEX IF NOT EXISTS rag_documents_fts_idx
  ON public.rag_documents USING gin(fts);

-- ===========================
-- ROW LEVEL SECURITY
-- ===========================

ALTER TABLE public.rag_documents ENABLE ROW LEVEL SECURITY;

-- Authenticated users can read all documents
DROP POLICY IF EXISTS "Allow authenticated users to read RAG documents" ON public.rag_documents;
CREATE POLICY "Allow authenticated users to read RAG documents"
  ON public.rag_documents
  FOR SELECT
  TO authenticated
  USING (true);

-- Anonymous users can read documents for public search
DROP POLICY IF EXISTS "Allow anonymous users to read RAG documents" ON public.rag_documents;
CREATE POLICY "Allow anonymous users to read RAG documents"
  ON public.rag_documents
  FOR SELECT
  TO anon
  USING (true);

-- Service role has full access for indexing
DROP POLICY IF EXISTS "Allow service role to manage RAG documents" ON public.rag_documents;
CREATE POLICY "Allow service role to manage RAG documents"
  ON public.rag_documents
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ===========================
-- SEARCH FUNCTIONS
-- ===========================

-- Simple semantic search function
CREATE OR REPLACE FUNCTION public.match_rag_documents (
  query_embedding vector(1536),
  filter_namespace TEXT DEFAULT NULL,
  match_threshold FLOAT DEFAULT 0.0,
  match_count INT DEFAULT 10
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  namespace TEXT,
  source_id TEXT,
  chunk_index INT,
  similarity FLOAT
)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  v_ef_search integer := COALESCE(
    NULLIF(current_setting('PGVECTOR_HNSW_EF_SEARCH_DEFAULT', true), '')::integer,
    96
  );
BEGIN
  PERFORM set_config('hnsw.ef_search', v_ef_search::text, true);
  RETURN QUERY
  SELECT
    d.id,
    d.content,
    d.metadata,
    d.namespace,
    d.source_id,
    d.chunk_index,
    1 - (d.embedding OPERATOR(extensions.<=>) query_embedding) AS similarity
  FROM public.rag_documents d
  WHERE
    (filter_namespace IS NULL OR d.namespace = filter_namespace) AND
    1 - (d.embedding OPERATOR(extensions.<=>) query_embedding) > match_threshold
  ORDER BY d.embedding OPERATOR(extensions.<=>) query_embedding
  LIMIT match_count;
END;
$$;

-- Hybrid search function (vector + lexical with RRF-style scoring)
CREATE OR REPLACE FUNCTION public.hybrid_rag_search (
  query_text TEXT,
  query_embedding vector(1536),
  filter_namespace TEXT DEFAULT NULL,
  match_count INT DEFAULT 10,
  match_threshold FLOAT DEFAULT 0.0,
  keyword_weight FLOAT DEFAULT 0.3,
  semantic_weight FLOAT DEFAULT 0.7
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  namespace TEXT,
  source_id TEXT,
  chunk_index INT,
  similarity FLOAT,
  keyword_rank FLOAT,
  combined_score FLOAT
)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  v_ef_search integer := COALESCE(
    NULLIF(current_setting('PGVECTOR_HNSW_EF_SEARCH_DEFAULT', true), '')::integer,
    96
  );
BEGIN
  PERFORM set_config('hnsw.ef_search', v_ef_search::text, true);
  RETURN QUERY
  WITH semantic_results AS (
    SELECT
      d.id,
      d.content,
      d.metadata,
      d.namespace,
      d.source_id,
      d.chunk_index,
      1 - (d.embedding OPERATOR(extensions.<=>) query_embedding) AS sim_score
    FROM public.rag_documents d
    WHERE
      (filter_namespace IS NULL OR d.namespace = filter_namespace) AND
      1 - (d.embedding OPERATOR(extensions.<=>) query_embedding) > match_threshold
    ORDER BY d.embedding OPERATOR(extensions.<=>) query_embedding
    LIMIT match_count * 2
  ),
	  keyword_results AS (
	    SELECT
	      d.id,
	      ts_rank_cd(d.fts, websearch_to_tsquery('english', query_text), 32) AS kw_rank
	    FROM public.rag_documents d
	    WHERE
	      (filter_namespace IS NULL OR d.namespace = filter_namespace) AND
	      d.fts @@ websearch_to_tsquery('english', query_text)
	    ORDER BY kw_rank DESC
	    LIMIT match_count * 2
	  )
  SELECT
    s.id,
    s.content,
    s.metadata,
    s.namespace,
    s.source_id,
    s.chunk_index,
    s.sim_score AS similarity,
    COALESCE(k.kw_rank, 0::FLOAT) AS keyword_rank,
    (s.sim_score * semantic_weight + COALESCE(k.kw_rank, 0::FLOAT) * keyword_weight) AS combined_score
  FROM semantic_results s
  LEFT JOIN keyword_results k ON s.id = k.id
  ORDER BY combined_score DESC
  LIMIT match_count;
END;
$$;

-- ===========================
-- COMMENTS
-- ===========================

COMMENT ON TABLE public.rag_documents IS 'Generic RAG document store with pgvector embeddings for semantic search (SPEC-0018)';
COMMENT ON COLUMN public.rag_documents.embedding IS 'Vector embedding (1536 dimensions) from OpenAI text-embedding-3-small';
COMMENT ON COLUMN public.rag_documents.namespace IS 'Logical partition for organizing documents by domain';
COMMENT ON COLUMN public.rag_documents.source_id IS 'Reference to original document for chunk lineage tracking';
COMMENT ON COLUMN public.rag_documents.chunk_index IS 'Index of chunk within source document (0-based)';
COMMENT ON COLUMN public.rag_documents.fts IS 'Full-text search tsvector for keyword matching';
COMMENT ON FUNCTION public.match_rag_documents IS 'Performs pure semantic search using vector similarity';
COMMENT ON FUNCTION public.hybrid_rag_search IS 'Performs hybrid search combining vector similarity and full-text matching';
