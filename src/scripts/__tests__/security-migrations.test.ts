/** @vitest-environment node */

import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const migrationsDir = join(process.cwd(), "supabase/migrations");
const hardeningMigrationName = "20260511010000_harden_api_keys_rls.sql";
const apiKeyRlsMigration = readFileSync(
  join(migrationsDir, hardeningMigrationName),
  "utf8"
);

describe("security hardening migrations", () => {
  it("keeps BYOK metadata mutation behind service-role paths", () => {
    expect(apiKeyRlsMigration).toContain(
      "REVOKE INSERT, UPDATE, DELETE ON TABLE public.api_keys FROM authenticated"
    );
    expect(apiKeyRlsMigration).toContain("CREATE POLICY api_keys_owner_select");
    expect(apiKeyRlsMigration).toContain("FOR SELECT");
    expect(apiKeyRlsMigration).toContain("TO authenticated");
    expect(apiKeyRlsMigration).toContain("CREATE POLICY api_keys_service");
    expect(apiKeyRlsMigration).toContain("TO service_role");
    expect(apiKeyRlsMigration).not.toMatch(
      /CREATE POLICY\s+api_keys_owner\b[\s\S]*?FOR ALL[\s\S]*?TO authenticated/
    );
  });

  it("does not reintroduce authenticated BYOK metadata write policies after hardening", () => {
    const laterActiveMigrationContents = readdirSync(migrationsDir)
      .filter((fileName) => fileName.endsWith(".sql"))
      .filter((fileName) => fileName > hardeningMigrationName)
      .map((fileName) => readFileSync(join(migrationsDir, fileName), "utf8"))
      .join("\n");

    expect(laterActiveMigrationContents).not.toMatch(
      /CREATE POLICY\s+api_keys_\w+\b[\s\S]*?FOR (?:ALL|INSERT|UPDATE|DELETE)[\s\S]*?TO authenticated/
    );
  });
});
