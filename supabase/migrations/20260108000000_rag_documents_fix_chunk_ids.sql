-- RAG documents: normalize chunk-suffixed IDs and ensure a composite primary key when needed.
-- Generated: 2026-01-08
--
-- Why:
-- - A recent change accidentally wrote chunk rows with `id = '<documentId>:<chunkIndex>'` while
--   upsert deduplicates on (id, chunk_index). This creates duplicate/stale rows on reindex.
-- - Some environments may also have an incorrect PRIMARY KEY on `id` only, which makes chunking
--   impossible. This migration makes that configuration safe by converting to a composite PK.
--
-- Safe to rerun: yes (idempotent checks).

BEGIN;

-- 1) If the table has an incorrect PRIMARY KEY on `id` only, convert to a composite PK (id, chunk_index).
DO $do$
DECLARE
  v_pk_cols text[];
  v_table regclass;
BEGIN
  SELECT to_regclass('public.rag_documents')
  INTO v_table;

  IF v_table IS NULL THEN
    RETURN;
  END IF;

  SELECT array_agg(a.attname ORDER BY array_position(i.indkey, a.attnum))
  INTO v_pk_cols
  FROM pg_index i
  JOIN pg_attribute a
    ON a.attrelid = i.indrelid
   AND a.attnum = ANY (i.indkey)
  WHERE i.indrelid = v_table
    AND i.indisprimary;

  IF v_pk_cols = ARRAY['id'] THEN
    ALTER TABLE public.rag_documents DROP CONSTRAINT IF EXISTS rag_documents_pkey;
  END IF;

  IF v_pk_cols IS NULL OR v_pk_cols = ARRAY['id'] THEN

    UPDATE public.rag_documents
    SET chunk_index = 0
    WHERE chunk_index IS NULL;

    ALTER TABLE public.rag_documents
      ALTER COLUMN chunk_index SET DEFAULT 0,
      ALTER COLUMN chunk_index SET NOT NULL;

    -- Create unique index and promote it to the primary key.
    CREATE UNIQUE INDEX IF NOT EXISTS rag_documents_pkey
      ON public.rag_documents (id, chunk_index);

    ALTER TABLE public.rag_documents
      ADD PRIMARY KEY USING INDEX rag_documents_pkey;
  END IF;
END;
$do$;

-- 2) Normalize chunk-suffixed IDs:
--    - Identify rows whose `id` ends with `:<digits>` and those digits match `chunk_index`.
--    - Upsert them into the canonical `(id, chunk_index)` key using the base id (without suffix).
--    - Delete the chunk-suffixed rows.
DO $do$
DECLARE
  v_id_type text;
  v_id_expr text;
BEGIN
  SELECT c.udt_name
  INTO v_id_type
  FROM information_schema.columns c
  WHERE c.table_schema = 'public'
    AND c.table_name = 'rag_documents'
    AND c.column_name = 'id';

  -- If the table is missing (shouldn't happen in prod), skip safely.
  IF v_id_type IS NULL THEN
    RETURN;
  END IF;

  -- Build an expression to convert the extracted base id into the target column type.
  -- `id` is expected to be UUID in most environments, but may be TEXT in some.
  v_id_expr := CASE
    WHEN v_id_type = 'uuid' THEN 'b.base_id_text::uuid'
    ELSE 'b.base_id_text'
  END;

  EXECUTE format($sql$
    WITH bad AS (
      SELECT
        d.id AS bad_id,
        d.chunk_index,
        regexp_replace(d.id::text, ':([0-9]+)$', '') AS base_id_text
      FROM public.rag_documents d
      WHERE d.chunk_index IS NOT NULL
        AND d.id::text ~ ':([0-9]+)$'
        AND right(d.id::text, length(d.chunk_index::text) + 1) = ':' || d.chunk_index::text
    )
    INSERT INTO public.rag_documents (
      id,
      chunk_index,
      content,
      embedding,
      metadata,
      namespace,
      source_id,
      user_id,
      trip_id,
      chat_id,
      created_at,
      updated_at
    )
    SELECT
      %s,
      d.chunk_index,
      d.content,
      d.embedding,
      d.metadata,
      d.namespace,
      d.source_id,
      d.user_id,
      d.trip_id,
      d.chat_id,
      d.created_at,
      d.updated_at
    FROM public.rag_documents d
    JOIN bad b
      ON b.bad_id = d.id
     AND b.chunk_index = d.chunk_index
    ON CONFLICT (id, chunk_index) DO UPDATE
      SET content = EXCLUDED.content,
          embedding = EXCLUDED.embedding,
          metadata = EXCLUDED.metadata,
          namespace = EXCLUDED.namespace,
          source_id = EXCLUDED.source_id,
          user_id = EXCLUDED.user_id,
          trip_id = EXCLUDED.trip_id,
          chat_id = EXCLUDED.chat_id,
          created_at = LEAST(public.rag_documents.created_at, EXCLUDED.created_at),
          updated_at = GREATEST(public.rag_documents.updated_at, EXCLUDED.updated_at);
    DELETE FROM public.rag_documents d
    USING bad b
    WHERE d.id = b.bad_id
      AND d.chunk_index = b.chunk_index;
  $sql$, v_id_expr);
END;
$do$;

COMMIT;
