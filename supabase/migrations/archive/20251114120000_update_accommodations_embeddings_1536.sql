-- Migrate accommodations embeddings + RPC to 1536 dimensions
BEGIN;

DROP INDEX IF EXISTS public.accommodation_embeddings_embedding_idx;

-- Clear existing embeddings (384-d) because they cannot be cast to 1536-d
UPDATE public.accommodation_embeddings
SET embedding = NULL
WHERE embedding IS NOT NULL;

-- Alter column type to 1536-d vectors
ALTER TABLE public.accommodation_embeddings
ALTER COLUMN embedding TYPE vector(1536)
USING embedding;

-- Recreate IVFFlat index for the new dimension
CREATE INDEX IF NOT EXISTS accommodation_embeddings_embedding_idx ON public.accommodation_embeddings
USING ivfflat (embedding vector_l2_ops)
WITH (lists = 100);

-- Update match_accommodation_embeddings RPC to accept 1536-d embeddings
CREATE OR REPLACE FUNCTION public.match_accommodation_embeddings (
  query_embedding vector(1536),
  match_threshold FLOAT DEFAULT 0.75,
  match_count INT DEFAULT 20
)
RETURNS TABLE (
  id TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    accom.id,
    1 - (accom.embedding <=> query_embedding) AS similarity
  FROM
    public.accommodation_embeddings AS accom
  WHERE accom.embedding IS NOT NULL
    AND 1 - (accom.embedding <=> query_embedding) > match_threshold
  ORDER BY
    similarity DESC
  LIMIT
    match_count;
END;
$$;

COMMENT ON COLUMN public.accommodation_embeddings.embedding IS 'Vector embedding (1536 dimensions) for semantic similarity search';
COMMENT ON FUNCTION public.match_accommodation_embeddings IS 'Performs semantic search on accommodations using 1536-d pgvector embeddings';

COMMIT;
