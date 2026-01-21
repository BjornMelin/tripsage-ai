-- Migration: Add match_turn_embeddings RPC function
-- Purpose: Enable semantic search over memory turn embeddings for context retrieval
-- This replaces the external Mem0 dependency with native Supabase pgvector search

-- NOTE: Supabase CLI can restore `supabase_migrations.schema_migrations` from a cached local backup.
-- If the tracking row for this migration already exists, the CLI will fail at the end when recording
-- the migration version. Make the migration idempotent by deleting any pre-existing row (when present).
DO $do$
BEGIN
  IF to_regclass('supabase_migrations.schema_migrations') IS NOT NULL THEN
    DELETE FROM supabase_migrations.schema_migrations WHERE version = '20251230000000';
  END IF;
END;
$do$;

-- Match turn embeddings for semantic memory search
-- Pattern follows match_rag_documents and match_accommodation_embeddings
CREATE OR REPLACE FUNCTION memories.match_turn_embeddings(
  query_embedding vector(1536),
  match_threshold FLOAT DEFAULT 0.7,
  match_count INT DEFAULT 10,
  filter_user_id UUID DEFAULT NULL,
  filter_session_id UUID DEFAULT NULL,
  ef_search_override INT DEFAULT NULL
)
RETURNS TABLE (
  turn_id UUID,
  session_id UUID,
  user_id UUID,
  content JSONB,
  role TEXT,
  similarity FLOAT,
  created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  v_jwt_role text := COALESCE(auth.jwt() ->> 'role', '');
  v_auth_uid uuid := auth.uid();
  v_effective_user_id uuid;
  v_ef_search integer := COALESCE(
    ef_search_override,
    NULLIF(current_setting('PGVECTOR_HNSW_EF_SEARCH_DEFAULT', true), '')::integer,
    96
  );
BEGIN
  -- SECURITY INVOKER keeps RLS in effect. Still enforce tenant scoping defensively.
  IF v_auth_uid IS NOT NULL THEN
    IF filter_user_id IS NULL THEN
      v_effective_user_id := v_auth_uid;
    ELSIF filter_user_id <> v_auth_uid THEN
      RAISE EXCEPTION 'filter_user_id must match authenticated user'
        USING ERRCODE = '42501';
    ELSE
      v_effective_user_id := filter_user_id;
    END IF;
  ELSE
    IF v_jwt_role = 'service_role' THEN
      IF filter_user_id IS NULL THEN
        RAISE EXCEPTION 'filter_user_id is required for service_role calls'
          USING ERRCODE = '22023';
      END IF;
      v_effective_user_id := filter_user_id;
    ELSE
      RAISE EXCEPTION 'authentication required'
        USING ERRCODE = '28000';
    END IF;
  END IF;

  IF match_count <= 0 THEN
    RAISE EXCEPTION 'match_count must be > 0'
      USING ERRCODE = '22023';
  END IF;

  IF match_threshold < 0 OR match_threshold > 1 THEN
    RAISE EXCEPTION 'match_threshold must be between 0 and 1'
      USING ERRCODE = '22023';
  END IF;

  IF ef_search_override IS NOT NULL AND (ef_search_override < 1 OR ef_search_override > 1000) THEN
    RAISE EXCEPTION 'ef_search_override must be between 1 and 1000'
      USING ERRCODE = '22023';
  END IF;

  -- Set HNSW ef_search for this query (higher = better recall, slower)
  PERFORM set_config('hnsw.ef_search', v_ef_search::text, true);

  RETURN QUERY
  SELECT
    te.turn_id,
    t.session_id,
    t.user_id,
    t.content,
    t.role,
    1 - (te.embedding OPERATOR(extensions.<=>) query_embedding) AS similarity,
    t.created_at
  FROM memories.turn_embeddings te
  JOIN memories.turns t ON t.id = te.turn_id
  WHERE
    -- Tenant scope: always enforced (authenticated => self, service_role => explicit user)
    t.user_id = v_effective_user_id
    -- Session filter: optional scope narrowing
    AND (filter_session_id IS NULL OR t.session_id = filter_session_id)
    -- Similarity threshold: exclude low-relevance matches
    AND 1 - (te.embedding OPERATOR(extensions.<=>) query_embedding) > match_threshold
  ORDER BY te.embedding OPERATOR(extensions.<=>) query_embedding
  LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION memories.match_turn_embeddings IS
  'Performs semantic search on memory turn embeddings using 1536-d pgvector (text-embedding-3-small). '
  'Returns turns matching the query embedding above the similarity threshold, ordered by relevance. '
  'Replaces external Mem0 dependency for context retrieval.';

-- Restrict RPC access: functions are EXECUTE-able by PUBLIC by default.
REVOKE EXECUTE ON FUNCTION memories.match_turn_embeddings(
  extensions.vector(1536),
  double precision,
  integer,
  uuid,
  uuid,
  integer
) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION memories.match_turn_embeddings(
  extensions.vector(1536),
  double precision,
  integer,
  uuid,
  uuid,
  integer
) TO authenticated, service_role;
