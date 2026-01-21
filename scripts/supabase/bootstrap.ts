import { run, supabaseDlxArgs } from "./supabase-cli";

function main() {
  // Full reset for local reproducibility (and aligns with Supabase CLI update guidance):
  // stop containers and delete volumes before proceeding with an upgrade.
  try {
    run("pnpm", supabaseDlxArgs(["stop", "--no-backup", "--yes"]));
  } catch {
    // Best-effort cleanup/bootstrapping
  }

  // Start core services and ensure Storage is healthy.
  run("pnpm", ["supabase:start"]);

  run("pnpm", supabaseDlxArgs(["status"]));
}

main();
