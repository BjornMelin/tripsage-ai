import { execFileSync } from "node:child_process";
import { supabaseDlxArgs } from "./supabase-cli";

function run(cmd: string, args: string[]): void {
  execFileSync(cmd, args, { stdio: "inherit" });
}

function main() {
  // Workaround: Supabase CLI `db reset` restarts services and triggers the broken Storage
  // healthcheck in this repo's setup. For a reproducible reset, do a clean stop (no backup)
  // and start the stack (which reapplies migrations).
  try {
    run("pnpm", supabaseDlxArgs(["stop", "--no-backup", "--yes"]));
  } catch {
    // Best-effort cleanup/bootstrapping
  }

  run("pnpm", ["supabase:start"]);
}

main();
