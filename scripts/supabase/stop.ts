import { execFileSync } from "node:child_process";
import { SUPABASE_PROJECT_ID, supabaseDlxArgs } from "./supabase-cli";

function tryRun(cmd: string, args: string[]): void {
  try {
    execFileSync(cmd, args, { stdio: "inherit" });
  } catch {
    // Best-effort cleanup
  }
}

function main() {
  // Stop Storage first (it may have been started outside the Supabase CLI).
  tryRun("docker", ["rm", "-f", `supabase_storage_${SUPABASE_PROJECT_ID}`]);

  // Let the CLI stop the rest (db, kong, auth, etc).
  tryRun("pnpm", supabaseDlxArgs(["stop"]));
}

main();
