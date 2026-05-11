-- Refresh seeded agent model defaults to the current repo-owned default.
-- Admin-created/custom provider model ids are left untouched; only seed rows
-- that drifted from the repo default are updated.

UPDATE public.agent_config AS active_config
SET
  config = jsonb_set(
    active_config.config,
    '{model}',
    to_jsonb('gpt-5.5'::text),
    true
  ),
  updated_at = now()
FROM public.agent_config_versions AS version
WHERE active_config.version_id = version.id
  AND version.summary = 'seed'
  AND active_config.config->>'model' IS DISTINCT FROM 'gpt-5.5';

UPDATE public.agent_config_versions
SET config = jsonb_set(
  config,
  '{model}',
  to_jsonb('gpt-5.5'::text),
  true
)
WHERE summary = 'seed'
  AND config->>'model' IS DISTINCT FROM 'gpt-5.5';
