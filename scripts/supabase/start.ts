import { ensureStorageRunning } from "./storage-local";
import { run, SUPABASE_PROJECT_ID, supabaseDlxArgs } from "./supabase-cli";

function main() {
  const projectId = SUPABASE_PROJECT_ID;

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
