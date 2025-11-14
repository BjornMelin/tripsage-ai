-- Create accommodations table with pg-vector support for RAG semantic search
-- This table stores property metadata and embeddings for hybrid search
-- (vector similarity + keyword filtering)

-- Vector extension is enabled in the base schema; do not re-enable here to
-- avoid schema conflicts when applying migrations to a fresh project.

-- Create accommodation embeddings table
CREATE TABLE IF NOT EXISTS public.accommodation_embeddings (
  id TEXT PRIMARY KEY, -- e.g., 'eps:12345'
  source TEXT NOT NULL CHECK (source IN ('hotel', 'vrbo')),
  name TEXT,
  description TEXT,
  amenities TEXT, -- JSON array or comma-separated string
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Vector embedding for semantic search (384 dimensions for Supabase/gte-small)
  embedding vector(384)
);

-- Create index for faster vector similarity search
-- IVFFlat index is optimized for approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS accommodation_embeddings_embedding_idx ON public.accommodation_embeddings
USING ivfflat (embedding vector_l2_ops)
WITH (lists = 100);

-- Create index on source for filtering
CREATE INDEX IF NOT EXISTS accommodation_embeddings_source_idx ON public.accommodation_embeddings(source);

-- Create index on created_at for recency sorting
CREATE INDEX IF NOT EXISTS accommodation_embeddings_created_at_idx ON public.accommodation_embeddings(created_at DESC);

CREATE OR REPLACE FUNCTION public.match_accommodation_embeddings (
  query_embedding vector(384),
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
  WHERE 1 - (accom.embedding <=> query_embedding) > match_threshold
  ORDER BY
    similarity DESC
  LIMIT
    match_count;
END;
$$;

-- Enable RLS on the embeddings table (trip-owned accommodations table RLS is
-- managed in the base schema).
ALTER TABLE public.accommodation_embeddings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow authenticated users to read accommodation embeddings"
  ON public.accommodation_embeddings
  FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Allow service role to manage accommodation embeddings"
  ON public.accommodation_embeddings
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Add comment
COMMENT ON TABLE public.accommodation_embeddings IS 'Stores accommodation property metadata and embeddings for RAG semantic search';
COMMENT ON COLUMN public.accommodation_embeddings.embedding IS 'Vector embedding (384 dimensions) for semantic similarity search';
COMMENT ON FUNCTION public.match_accommodation_embeddings IS 'Performs semantic search on accommodations using vector similarity';
