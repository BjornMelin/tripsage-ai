-- Seed baseline agent configuration (idempotent)
-- Created: 2025-11-22

DO $$
DECLARE
  agents constant text[] := array[
    'budgetAgent',
    'destinationResearchAgent',
    'itineraryAgent',
    'flightAgent',
    'accommodationAgent',
    'memoryAgent'
  ];
  agent text;
  version_id uuid;
  cfg jsonb;
BEGIN
  FOREACH agent IN ARRAY agents LOOP
    cfg := jsonb_build_object(
      'agentType', agent,
      'createdAt', to_char(now(), 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'),
      'updatedAt', to_char(now(), 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'),
      'id', concat('v', extract(epoch from now())::bigint, '_seed_', agent),
      'model', 'gpt-4o',
      'parameters', jsonb_build_object(
        'temperature', 0.3,
        'maxTokens', 4096,
        'topP', 0.9
      ),
      'scope', 'global'
    );

    INSERT INTO public.agent_config_versions(agent_type, scope, config, summary)
    VALUES (agent, 'global', cfg, 'seed')
    ON CONFLICT DO NOTHING
    RETURNING id INTO version_id;

    IF version_id IS NULL THEN
      SELECT id INTO version_id FROM public.agent_config_versions
      WHERE agent_type = agent AND scope = 'global'
      ORDER BY created_at DESC LIMIT 1;
    END IF;

    INSERT INTO public.agent_config(agent_type, scope, config, version_id)
    VALUES (agent, 'global', cfg, version_id)
    ON CONFLICT (agent_type, scope) DO UPDATE SET
      config = EXCLUDED.config,
      version_id = EXCLUDED.version_id,
      updated_at = now();
  END LOOP;
END$$;
