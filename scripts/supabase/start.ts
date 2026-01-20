import { execFileSync } from "node:child_process";
import { ensureStorageRunning } from "./storage-local";
import { supabaseDlxArgs } from "./supabase-cli";

function run(cmd: string, args: string[]): void {
  execFileSync(cmd, args, { stdio: "inherit" });
}

function getProjectId(): string {
  // Keep it simple and consistent with supabase/config.toml.
  return "tripsage-ai";
}

function main() {
  const projectId = getProjectId();

  // Workaround: Supabase CLI 2.72.8 `supabase start` fails health checks when `storage-api`
  // is started directly by the CLI in this repo's setup. Start the core stack first, then
  // start Storage with an env derived from kong/gotrue/postgrest.
  run(
    "pnpm",
    supabaseDlxArgs(["start", "--yes", "--exclude", "storage-api,edge-runtime"])
  );

  ensureStorageRunning({ projectId, supabaseDir: "supabase" });
}

main();
