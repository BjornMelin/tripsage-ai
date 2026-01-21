import { execFileSync } from "node:child_process";

export const SUPABASE_CLI_VERSION = "2.72.8" as const;
export const SUPABASE_PROJECT_ID = "tripsage-ai" as const;
export const STORAGE_API_IMAGE_VERSION = "v1.33.5" as const;

export function run(cmd: string, args: string[]): void {
  execFileSync(cmd, args, { stdio: "inherit" });
}

export function supabaseDlxArgs(args: string[]): string[] {
  return ["dlx", `supabase@${SUPABASE_CLI_VERSION}`, ...args];
}
