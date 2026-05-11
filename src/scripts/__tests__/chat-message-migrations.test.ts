/** @vitest-environment node */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const migration = readFileSync(
  join(
    process.cwd(),
    "supabase/migrations/20260511020000_canonicalize_chat_message_parts.sql"
  ),
  "utf8"
);

describe("chat message persistence migrations", () => {
  it("removes tool-shaped UI parts from persisted message content", () => {
    expect(migration).toContain("public.chat_tool_calls");
    expect(migration).toContain("WITH ORDINALITY AS parts(part, ord)");
    expect(migration).toContain("grouped_tool_calls");
    expect(migration).toContain("provider_executed");
    expect(migration).toContain("message_record.role = 'assistant'");
    expect(migration).not.toContain("message_record.metadata ? 'requestId'");
    expect(migration).not.toContain("message_record.metadata ? 'provider'");
    expect(migration).not.toContain("message_record.metadata ? 'uiMessageId'");
    expect(migration).toContain("part->>'type' = 'dynamic-tool'");
    expect(migration).toContain("part->>'type' = 'tool-call'");
    expect(migration).toContain("part->>'type' LIKE 'tool-%'");
    expect(migration).toContain("jsonb_agg(part ORDER BY ord)");
    expect(migration).toContain("SET content = canonical_parts::text");
  });

  it("keeps messages renderable when every stored part was a tool part", () => {
    expect(migration).toContain(
      `canonical_parts := '[{"type":"text","text":""}]'::jsonb`
    );
  });

  it("refreshes only seeded legacy agent model defaults", () => {
    const migration = readFileSync(
      join(
        process.cwd(),
        "supabase/migrations/20260511021000_refresh_agent_config_model_defaults.sql"
      ),
      "utf8"
    );

    expect(migration).toContain("public.agent_config AS active_config");
    expect(migration).toContain("public.agent_config_versions AS version");
    expect(migration).toContain("version.summary = 'seed'");
    expect(migration).toContain("to_jsonb('gpt-5.5'::text)");
    expect(migration).toContain(
      "active_config.config->>'model' IS DISTINCT FROM 'gpt-5.5'"
    );
  });

  it("hardens existing Gateway and tool-call schema contracts", () => {
    const migration = readFileSync(
      join(
        process.cwd(),
        "supabase/migrations/20260511019000_harden_gateway_tool_call_contracts.sql"
      ),
      "utf8"
    );

    expect(migration).toContain("ADD COLUMN IF NOT EXISTS provider_executed");
    expect(migration).toContain("SET provider_executed = false");
    expect(migration).toContain("ALTER COLUMN provider_executed SET DEFAULT false");
    expect(migration).toContain("ALTER COLUMN provider_executed SET NOT NULL");
    expect(migration).toContain("CREATE POLICY chat_messages_insert");
    expect(migration).toContain("AND role = 'user'");
    expect(migration).toContain("CREATE POLICY chat_messages_service_insert");
    expect(migration).toContain("CREATE POLICY chat_tool_calls_insert");
    expect(migration).toContain(
      "CREATE POLICY chat_tool_calls_insert\n  ON public.chat_tool_calls\n  FOR INSERT\n  TO service_role"
    );
    expect(migration).toContain(
      "CREATE POLICY api_gateway_configs_owner\n  ON public.api_gateway_configs\n  FOR SELECT\n  TO authenticated"
    );
    expect(migration).toContain("USING ((select auth.uid()) = user_id)");
    expect(migration).toContain(
      "ALTER COLUMN allow_gateway_fallback SET DEFAULT false"
    );
    expect(migration).toContain("RETURN coalesce(v_flag, false)");
    expect(migration).toContain(
      "REVOKE ALL ON FUNCTION public.get_user_allow_gateway_fallback(uuid) FROM PUBLIC"
    );
  });

  it("preserves legacy tool parts when canonicalization is incomplete", () => {
    const migration = readFileSync(
      join(
        process.cwd(),
        "supabase/migrations/20260511020000_canonicalize_chat_message_parts.sql"
      ),
      "utf8"
    );

    expect(migration).toContain("should_strip_tool_parts := false");
    expect(migration).toContain("raw_parts.tool_id IS NULL");
    expect(migration).toContain("grouped_tool_calls.tool_name IS NULL");
    expect(migration).toContain(
      "WHERE raw_parts.tool_id IS NULL\n          OR grouped_tool_calls.tool_name IS NULL\n      ) THEN\n        CONTINUE;"
    );
    expect(migration).toContain("should_strip_tool_parts := true");
    expect(migration).toContain(
      "CASE WHEN status IN ('completed', 'failed') THEN message_record.created_at ELSE NULL END"
    );
  });

  it("keeps the consolidated baseline aligned with Gateway and chat hardening", () => {
    const baseline = readFileSync(
      join(
        process.cwd(),
        "supabase/migrations/archive/20260120_predeploy_consolidation/20251122000000_base_schema.sql"
      ),
      "utf8"
    );

    expect(baseline).toContain(
      "role TEXT NOT NULL CHECK (role IN ('user','assistant','system','tool'))"
    );
    expect(baseline).toContain("allow_gateway_fallback BOOLEAN NOT NULL DEFAULT FALSE");
    expect(baseline).toContain("RETURN coalesce(v_flag, false)");
    expect(baseline).toContain(
      "CREATE POLICY api_gateway_configs_owner ON public.api_gateway_configs FOR SELECT TO authenticated USING ((select auth.uid()) = user_id)"
    );
    expect(baseline).not.toContain(
      "CREATE POLICY api_gateway_configs_owner ON public.api_gateway_configs FOR ALL TO authenticated"
    );
  });
});
