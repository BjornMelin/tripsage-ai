export const SUPABASE_CLI_VERSION = "2.72.8" as const;

export function supabaseDlxArgs(args: string[]): string[] {
  return ["dlx", `supabase@${SUPABASE_CLI_VERSION}`, ...args];
}
