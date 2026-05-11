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
    expect(migration).toContain("message_record.metadata ? 'requestId'");
    expect(migration).toContain("message_record.metadata ? 'provider'");
    expect(migration).toContain("message_record.metadata ? 'uiMessageId'");
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
    expect(migration).toContain("CREATE POLICY chat_messages_insert");
    expect(migration).toContain("AND role = 'user'");
    expect(migration).toContain("CREATE POLICY chat_messages_service_insert");
    expect(migration).toContain(
      "ALTER COLUMN allow_gateway_fallback SET DEFAULT false"
    );
    expect(migration).toContain("RETURN coalesce(v_flag, false)");
    expect(migration).toContain("FOR INSERT");
    expect(migration).toContain("TO service_role");
    expect(migration).toContain("FOR SELECT");
  });
});
