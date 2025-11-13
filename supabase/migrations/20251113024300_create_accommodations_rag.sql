-- Create accommodations table with pg-vector support for RAG semantic search
-- This table stores property metadata and embeddings for hybrid search
-- (vector similarity + keyword filtering)

-- Enable vector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

-- Create accommodations table
CREATE TABLE IF NOT EXISTS public.accommodations (
  id TEXT PRIMARY KEY, -- e.g., 'eps:12345'
  source TEXT NOT NULL CHECK (source IN ('hotel', 'vrbo')),
  name TEXT,
  description TEXT,
  amenities TEXT, -- JSON array or comma-separated string
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Vector embedding for semantic search (384 dimensions for Supabase/gte-small)
  embedding extensions.vector(384)
);

-- Create index for faster vector similarity search
-- IVFFlat index is optimized for approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS accommodations_embedding_idx ON public.accommodations
USING ivfflat (embedding extensions.vector_l2_ops)
WITH (lists = 100);

-- Create index on source for filtering
CREATE INDEX IF NOT EXISTS accommodations_source_idx ON public.accommodations(source);

-- Create index on created_at for recency sorting
CREATE INDEX IF NOT EXISTS accommodations_created_at_idx ON public.accommodations(created_at DESC);

-- Create function to perform semantic search (RAG)
CREATE OR REPLACE FUNCTION public.match_accommodations (
  query_embedding extensions.vector(384),
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
    public.accommodations AS accom
  WHERE 1 - (accom.embedding <=> query_embedding) > match_threshold
  ORDER BY
    similarity DESC
  LIMIT
    match_count;
END;
$$;

-- Add RLS policies (if RLS is enabled)
ALTER TABLE public.accommodations ENABLE ROW LEVEL SECURITY;

-- Policy: Allow authenticated users to read accommodations
CREATE POLICY "Allow authenticated users to read accommodations"
  ON public.accommodations
  FOR SELECT
  TO authenticated
  USING (true);

-- Policy: Allow service role to manage accommodations (for embedding generation)
CREATE POLICY "Allow service role to manage accommodations"
  ON public.accommodations
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Add comment
COMMENT ON TABLE public.accommodations IS 'Stores accommodation property metadata and embeddings for RAG semantic search';
COMMENT ON COLUMN public.accommodations.embedding IS 'Vector embedding (384 dimensions) for semantic similarity search';
COMMENT ON FUNCTION public.match_accommodations IS 'Performs semantic search on accommodations using vector similarity';

