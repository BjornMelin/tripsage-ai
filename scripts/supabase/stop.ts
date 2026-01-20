import { execFileSync } from "node:child_process";
import { supabaseDlxArgs } from "./supabase-cli";

function tryRun(cmd: string, args: string[]): void {
  try {
    execFileSync(cmd, args, { stdio: "inherit" });
  } catch {
    // Best-effort cleanup
  }
}

function main() {
  // Stop Storage first (it may have been started outside the Supabase CLI).
  tryRun("docker", ["rm", "-f", "supabase_storage_tripsage-ai"]);

  // Let the CLI stop the rest (db, kong, auth, etc).
  tryRun("pnpm", supabaseDlxArgs(["stop"]));
}

main();
