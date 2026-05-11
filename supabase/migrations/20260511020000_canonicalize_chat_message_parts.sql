-- Canonicalize persisted chat message content for AI SDK v6.
-- Tool invocation lifecycle is stored in public.chat_tool_calls; message content
-- must only contain renderable non-tool UIMessage parts.

DO $$
DECLARE
  canonical_parts jsonb;
  message_record record;
  parsed_parts jsonb;
  should_strip_tool_parts boolean;
BEGIN
  FOR message_record IN
    SELECT id, content, metadata, role, created_at
    FROM public.chat_messages
    WHERE content ~ '^\s*\['
  LOOP
    should_strip_tool_parts := false;

    BEGIN
      parsed_parts := message_record.content::jsonb;
    EXCEPTION WHEN others THEN
      CONTINUE;
    END;

    IF jsonb_typeof(parsed_parts) <> 'array' THEN
      CONTINUE;
    END IF;

    IF message_record.role = 'assistant' THEN
      IF EXISTS (
        WITH raw_parts AS (
          SELECT
            part,
            ord,
            part->>'type' AS part_type,
            coalesce(
              nullif(part->>'toolCallId', ''),
              nullif(part->>'tool_call_id', ''),
              nullif(part->>'toolId', ''),
              nullif(part->>'id', '')
            ) AS tool_id
          FROM jsonb_array_elements(parsed_parts) WITH ORDINALITY AS parts(part, ord)
          WHERE jsonb_typeof(part) = 'object'
            AND (
              part->>'type' = 'dynamic-tool'
              OR part->>'type' = 'tool-call'
              OR part->>'type' = 'tool-result'
              OR part->>'type' = 'tool-approval-request'
              OR part->>'type' = 'tool-approval-response'
              OR part->>'type' LIKE 'tool-%'
              OR part->>'type' LIKE 'tool-input-%'
              OR part->>'type' LIKE 'tool-output-%'
            )
        ),
        normalized_parts AS (
          SELECT
            tool_id,
            coalesce(
              nullif(part->>'toolName', ''),
              nullif(part->>'tool_name', ''),
              CASE
                WHEN part_type LIKE 'tool-%'
                  AND part_type NOT LIKE 'tool-input-%'
                  AND part_type NOT LIKE 'tool-output-%'
                  AND part_type NOT IN (
                    'tool-call',
                    'tool-result',
                    'tool-approval-request',
                    'tool-approval-response'
                  )
                  THEN substring(part_type from 6)
                ELSE NULL
              END
            ) AS tool_name
          FROM raw_parts
        ),
        grouped_tool_calls AS (
          SELECT
            tool_id,
            (array_agg(tool_name) FILTER (WHERE tool_name IS NOT NULL))[1] AS tool_name
          FROM normalized_parts
          WHERE tool_id IS NOT NULL
          GROUP BY tool_id
        )
        SELECT 1
        FROM raw_parts
        LEFT JOIN grouped_tool_calls USING (tool_id)
        WHERE raw_parts.tool_id IS NULL
          OR grouped_tool_calls.tool_name IS NULL
      ) THEN
        CONTINUE;
      END IF;

      WITH raw_parts AS (
        SELECT
          part,
          ord,
          part->>'type' AS part_type,
          coalesce(
            nullif(part->>'toolCallId', ''),
            nullif(part->>'tool_call_id', ''),
            nullif(part->>'toolId', ''),
            nullif(part->>'id', '')
          ) AS tool_id
        FROM jsonb_array_elements(parsed_parts) WITH ORDINALITY AS parts(part, ord)
        WHERE jsonb_typeof(part) = 'object'
          AND (
            part->>'type' = 'dynamic-tool'
            OR part->>'type' = 'tool-call'
            OR part->>'type' = 'tool-result'
            OR part->>'type' = 'tool-approval-request'
            OR part->>'type' = 'tool-approval-response'
            OR part->>'type' LIKE 'tool-%'
            OR part->>'type' LIKE 'tool-input-%'
            OR part->>'type' LIKE 'tool-output-%'
          )
      ),
      normalized_parts AS (
        SELECT
          tool_id,
          ord,
          coalesce(
            nullif(part->>'toolName', ''),
            nullif(part->>'tool_name', ''),
            CASE
              WHEN part_type LIKE 'tool-%'
                AND part_type NOT LIKE 'tool-input-%'
                AND part_type NOT LIKE 'tool-output-%'
                AND part_type NOT IN (
                  'tool-call',
                  'tool-result',
                  'tool-approval-request',
                  'tool-approval-response'
                )
                THEN substring(part_type from 6)
              ELSE NULL
            END
          ) AS tool_name,
          coalesce(part->'input', part->'arguments', part->'args') AS arguments,
          coalesce(part->'output', part->'result') AS result,
          coalesce(
            nullif(part->>'errorText', ''),
            nullif(part->>'error', '')
          ) AS error_message,
          CASE
            WHEN lower(coalesce(part->>'providerExecuted', part->>'provider_executed', '')) = 'true'
              THEN true
            ELSE false
          END AS provider_executed,
          (
            part->>'state' = 'output-error'
            OR part ? 'errorText'
            OR part ? 'error'
          ) AS is_failed,
          (
            part->>'type' = 'tool-result'
            OR part->>'state' = 'output-available'
            OR part ? 'output'
            OR part ? 'result'
          ) AS is_completed
        FROM raw_parts
        WHERE tool_id IS NOT NULL
      ),
      grouped_tool_calls AS (
        SELECT
          tool_id,
          (array_agg(tool_name ORDER BY ord) FILTER (WHERE tool_name IS NOT NULL))[1] AS tool_name,
          coalesce(
            (array_agg(arguments ORDER BY ord) FILTER (WHERE arguments IS NOT NULL))[1],
            '{}'::jsonb
          ) AS arguments,
          (array_agg(result ORDER BY ord DESC) FILTER (WHERE result IS NOT NULL))[1] AS result,
          CASE
            WHEN bool_or(is_failed) THEN 'failed'
            WHEN bool_or(is_completed) THEN 'completed'
            ELSE 'pending'
          END AS status,
          bool_or(provider_executed) AS provider_executed,
          (array_agg(error_message ORDER BY ord DESC) FILTER (WHERE error_message IS NOT NULL))[1] AS error_message
        FROM normalized_parts
        GROUP BY tool_id
      )
      INSERT INTO public.chat_tool_calls (
        message_id,
        tool_id,
        tool_name,
        arguments,
        result,
        status,
        provider_executed,
        completed_at,
        error_message
      )
      SELECT
        message_record.id,
        tool_id,
        tool_name,
        arguments,
        result,
        status,
        provider_executed,
        CASE WHEN status IN ('completed', 'failed') THEN message_record.created_at ELSE NULL END,
        error_message
      FROM grouped_tool_calls
      WHERE tool_name IS NOT NULL
        AND NOT EXISTS (
          SELECT 1
          FROM public.chat_tool_calls existing
          WHERE existing.message_id = message_record.id
            AND existing.tool_id = grouped_tool_calls.tool_id
        );

      should_strip_tool_parts := true;
    END IF;

    IF should_strip_tool_parts THEN
      SELECT COALESCE(jsonb_agg(part ORDER BY ord), '[]'::jsonb)
      INTO canonical_parts
      FROM jsonb_array_elements(parsed_parts) WITH ORDINALITY AS parts(part, ord)
      WHERE NOT (
        jsonb_typeof(part) = 'object'
        AND (
          part->>'type' = 'dynamic-tool'
          OR part->>'type' = 'tool-call'
          OR part->>'type' = 'tool-result'
          OR part->>'type' = 'tool-approval-request'
          OR part->>'type' = 'tool-approval-response'
          OR part->>'type' LIKE 'tool-%'
          OR part->>'type' LIKE 'tool-input-%'
          OR part->>'type' LIKE 'tool-output-%'
        )
      );
    ELSE
      canonical_parts := parsed_parts;
    END IF;

    IF canonical_parts = '[]'::jsonb THEN
      canonical_parts := '[{"type":"text","text":""}]'::jsonb;
    END IF;

    IF canonical_parts IS DISTINCT FROM parsed_parts THEN
      UPDATE public.chat_messages
      SET content = canonical_parts::text
      WHERE id = message_record.id;
    END IF;
  END LOOP;
END $$;
