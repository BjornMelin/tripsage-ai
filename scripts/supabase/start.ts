import { execFileSync } from "node:child_process";
import { ensureStorageRunning } from "./storage-local";
import { run, SUPABASE_PROJECT_ID, supabaseDlxArgs } from "./supabase-cli";

function main() {
  // Clean up any legacy storage container created by previous custom startup flows.
  const storageContainer = `supabase_storage_${SUPABASE_PROJECT_ID}`;
  try {
    execFileSync("docker", ["rm", "-f", storageContainer], {
      stdio: "ignore",
    });
  } catch {
    // Best-effort cleanup; ignore if container doesn't exist.
  }

  // Workaround: Supabase CLI 2.72.8 `supabase start` fails health checks when
  // `storage-api` is started directly by the CLI in this repo's setup.
  run(
    "pnpm",
    supabaseDlxArgs(["start", "--yes", "--exclude", "storage-api,edge-runtime"])
  );

  ensureStorageRunning({ projectId: SUPABASE_PROJECT_ID, supabaseDir: "supabase" });
}

main();
