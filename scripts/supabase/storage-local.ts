import { execFileSync } from "node:child_process";
import { STORAGE_API_IMAGE_VERSION } from "./supabase-cli";

type LocalSupabaseIds = {
  projectId: string;
  networkId: string;
  kongId: string;
  authId: string;
  restId: string;
  dbId: string;
  storageId: string;
};

function getIdsFromProjectId(projectId: string): LocalSupabaseIds {
  return {
    authId: `supabase_auth_${projectId}`,
    dbId: `supabase_db_${projectId}`,
    kongId: `supabase_kong_${projectId}`,
    networkId: `supabase_network_${projectId}`,
    projectId,
    restId: `supabase_rest_${projectId}`,
    storageId: `supabase_storage_${projectId}`,
  };
}

function sh(cmd: string, args: string[]): string {
  return execFileSync(cmd, args, {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  }).trim();
}

function trySh(cmd: string, args: string[]): string | null {
  try {
    return sh(cmd, args);
  } catch {
    return null;
  }
}

function decodeJwtPayload(token: string): unknown {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const payloadJson = Buffer.from(parts[1], "base64url").toString("utf8");
  try {
    return JSON.parse(payloadJson) as unknown;
  } catch {
    return null;
  }
}

function readKongConfigYaml(kongId: string): string {
  return sh("docker", ["exec", kongId, "sh", "-lc", "cat /home/kong/kong.yml"]);
}

function extractFirstMatch(text: string, re: RegExp): string | null {
  const match = re.exec(text);
  return match?.[0] ?? null;
}

function extractAll(text: string, re: RegExp): string[] {
  const matches: string[] = [];
  for (const match of text.matchAll(re)) {
    if (match[1]) matches.push(match[1]);
  }
  return matches;
}

function unique(items: string[]): string[] {
  return Array.from(new Set(items));
}

function getPublishableKey(kongYaml: string): string {
  const key = extractFirstMatch(kongYaml, /\bsb_publishable_[A-Za-z0-9_-]+\b/);
  if (!key) throw new Error("Could not find sb_publishable_* key in kong.yml");
  return key;
}

function getSecretKey(kongYaml: string): string {
  const key = extractFirstMatch(kongYaml, /\bsb_secret_[A-Za-z0-9_-]+\b/);
  if (!key) throw new Error("Could not find sb_secret_* key in kong.yml");
  return key;
}

function getBearerRoleTokens(kongYaml: string): { anon: string; serviceRole: string } {
  const bearerTokens = unique(
    extractAll(
      kongYaml,
      /\bBearer\s+(eyJ[0-9A-Za-z_-]+\.[0-9A-Za-z_-]+\.[0-9A-Za-z_-]+)\b/g
    )
  );

  let anon: string | null = null;
  let serviceRole: string | null = null;

  for (const token of bearerTokens) {
    const payload = decodeJwtPayload(token);
    if (!payload || typeof payload !== "object") continue;
    const role = (payload as Record<string, unknown>).role;
    if (role === "anon") anon = token;
    if (role === "service_role") serviceRole = token;
  }

  if (!anon || !serviceRole) {
    throw new Error(
      `Could not resolve role tokens from kong.yml (anon=${Boolean(anon)} service_role=${Boolean(
        serviceRole
      )})`
    );
  }

  return { anon, serviceRole };
}

function getContainerEnvValue(containerId: string, envVar: string): string {
  const envList = sh("docker", [
    "inspect",
    containerId,
    "--format",
    "{{range .Config.Env}}{{println .}}{{end}}",
  ]);
  const line = envList
    .split("\n")
    .map((l) => l.trim())
    .find((l) => l.startsWith(`${envVar}=`));
  if (!line) throw new Error(`Missing ${envVar} in ${containerId} env`);
  return line.slice(envVar.length + 1);
}

function getDbPassword(dbId: string): string {
  const pw = trySh("docker", [
    "exec",
    dbId,
    "sh",
    "-lc",
    'printf %s "$POSTGRES_PASSWORD"',
  ]);
  if (pw && pw.length > 0) return pw;
  return "postgres";
}

function waitForStorageReady(apiKey: string, label: string): void {
  const maxAttempts = 10;
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const ready = trySh("curl", [
      "-sSfL",
      "-H",
      `apikey: ${apiKey}`,
      "http://127.0.0.1:54321/storage/v1/bucket",
      "-o",
      "/dev/null",
    ]);
    if (ready !== null) return;
    if (attempt === maxAttempts) {
      throw new Error(`Storage container failed to become ready for ${label} key`);
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 500);
  }
}

export type EnsureStorageOptions = {
  projectId: string;
  supabaseDir: string;
};

export function ensureStorageRunning(opts: EnsureStorageOptions): void {
  const ids = getIdsFromProjectId(opts.projectId);

  // Ensure we have a reachable kong + auth + rest (otherwise, storage wiring can't be derived).
  sh("docker", ["inspect", ids.kongId]);
  sh("docker", ["inspect", ids.authId]);
  sh("docker", ["inspect", ids.restId]);
  sh("docker", ["inspect", ids.dbId]);

  const kongYaml = readKongConfigYaml(ids.kongId);
  const publishableKey = getPublishableKey(kongYaml);
  const secretKey = getSecretKey(kongYaml);
  const { anon: anonJwt, serviceRole: serviceJwt } = getBearerRoleTokens(kongYaml);

  const dbPassword = getDbPassword(ids.dbId);
  const authJwtSecret = getContainerEnvValue(ids.authId, "GOTRUE_JWT_SECRET");
  const jwks = getContainerEnvValue(ids.restId, "PGRST_JWT_SECRET");

  const storageMigrationFile = `${opts.supabaseDir}/.temp/storage-migration`;
  const storageMigration = trySh("cat", [storageMigrationFile]);
  if (!storageMigration) {
    throw new Error(
      `Storage migration file not found at ${storageMigrationFile}. ` +
        "Run 'pnpm supabase:bootstrap' first to initialize local Supabase."
    );
  }

  // Replace any existing container (e.g., from prior runs).
  trySh("docker", ["rm", "-f", ids.storageId]);

  // Keep the volume name aligned with the CLI default to preserve persisted files.
  const volumeName = ids.storageId;
  trySh("docker", ["volume", "create", volumeName]);

  sh("docker", [
    "run",
    "-d",
    "--name",
    ids.storageId,
    "--network",
    ids.networkId,
    "--restart",
    "unless-stopped",
    "-v",
    `${volumeName}:/mnt`,
    "-e",
    `DB_MIGRATIONS_FREEZE_AT=${storageMigration}`,
    "-e",
    `ANON_KEY=${anonJwt}`,
    "-e",
    `SERVICE_KEY=${serviceJwt}`,
    "-e",
    `AUTH_JWT_SECRET=${authJwtSecret}`,
    "-e",
    `JWT_JWKS=${jwks}`,
    "-e",
    `DATABASE_URL=postgresql://supabase_storage_admin:${dbPassword}@${ids.dbId}:5432/postgres`,
    "-e",
    "FILE_SIZE_LIMIT=50MiB",
    "-e",
    "STORAGE_BACKEND=file",
    "-e",
    "FILE_STORAGE_BACKEND_PATH=/mnt",
    "-e",
    "TENANT_ID=stub",
    "-e",
    "STORAGE_S3_REGION=stub",
    "-e",
    "GLOBAL_S3_BUCKET=stub",
    "-e",
    "ENABLE_IMAGE_TRANSFORMATION=false",
    "-e",
    "TUS_URL_PATH=/storage/v1/upload/resumable",
    "-e",
    "S3_PROTOCOL_ENABLED=false",
    `public.ecr.aws/supabase/storage-api:${STORAGE_API_IMAGE_VERSION}`,
  ]);

  // Quick sanity check through kong (ensures routing + auth headers work).
  waitForStorageReady(publishableKey, "publishable");
  waitForStorageReady(secretKey, "secret");
}
