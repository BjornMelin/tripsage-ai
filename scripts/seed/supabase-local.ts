#!/usr/bin/env tsx

/**
 * @fileoverview Deterministic local seed data for Supabase (scenario-focused profiles).
 *
 * Usage:
 *   pnpm supabase:seed:dev
 *   pnpm supabase:seed:e2e
 *   pnpm supabase:seed:payments
 *   pnpm supabase:seed:calendar
 *   pnpm supabase:seed:edge-cases
 *
 * Requirements:
 * - NEXT_PUBLIC_SUPABASE_URL (local or remote)
 * - SUPABASE_SERVICE_ROLE_KEY (server-only; never expose client-side)
 */

// biome-ignore-all lint/style/useNamingConvention: Supabase APIs and DB columns require snake_case keys.

import { execSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { basename } from "node:path";
import { openai } from "@ai-sdk/openai";
import { createClient } from "@supabase/supabase-js";
import { embedMany } from "ai";
import { z } from "zod";
import {
  DETERMINISTIC_TEXT_EMBEDDING_MODEL_ID,
  deterministicTextEmbedding,
} from "../../src/lib/ai/embeddings/deterministic";

// Canonical source: src/lib/ai/embeddings/text-embedding-model.ts
// Intentional duplication to keep seed script self-contained and avoid "server-only" imports.
const TEXT_EMBEDDING_DIMENSIONS = 1536;

import type { Database, Json } from "../../src/lib/supabase/database.types";
import { SUPABASE_CLI_VERSION } from "../supabase/supabase-cli";

type SeedProfile = "dev" | "e2e" | "payments" | "calendar" | "edge-cases";

const envSchema = z.object({
  serviceRoleKey: z.string().min(1),
  storageUrl: z.url().optional(),
  supabaseUrl: z.url(),
});

const argvProfile = process.argv
  .find((arg) => arg.startsWith("--profile="))
  ?.slice("--profile=".length);

const profile: SeedProfile =
  argvProfile === "e2e" ||
  argvProfile === "dev" ||
  argvProfile === "payments" ||
  argvProfile === "calendar" ||
  argvProfile === "edge-cases"
    ? argvProfile
    : "dev";

function parseSupabaseStatusEnv(output: string): Record<string, string> {
  const result: Record<string, string> = {};
  for (const rawLine of output.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) continue;
    const match = line.match(/^([A-Z0-9_]+)=(?:"([^"]*)"|(.+))$/);
    if (!match) continue;
    const key = match[1] ?? "";
    const quoted = match[2];
    const unquoted = match[3];
    const value = quoted ?? unquoted ?? "";
    if (!key || !value) continue;
    result[key] = value;
  }
  return result;
}

function resolveLocalSupabaseEnvFallback(): {
  serviceRoleKey?: string;
  supabaseUrl?: string;
} {
  try {
    const output = execSync(
      `pnpm dlx supabase@${SUPABASE_CLI_VERSION} status --output env`,
      {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "pipe"],
      }
    );
    const parsed = parseSupabaseStatusEnv(output);
    return {
      // Supabase status outputs both:
      // - SECRET_KEY (sb_secret_...) for API requests (preferred)
      // - SERVICE_ROLE_KEY (JWT) for legacy flows
      serviceRoleKey: parsed.SECRET_KEY ?? parsed.SERVICE_ROLE_KEY,
      supabaseUrl: parsed.API_URL,
    };
  } catch {
    return {};
  }
}

const localFallback =
  process.env.SUPABASE_SERVICE_ROLE_KEY && process.env.NEXT_PUBLIC_SUPABASE_URL
    ? {}
    : resolveLocalSupabaseEnvFallback();

const storageUrlRaw = process.env.SUPABASE_STORAGE_URL?.trim();
const storageUrl = storageUrlRaw?.replace(/\/storage\/v1\/?$/, "") || undefined;

const env = envSchema.parse({
  serviceRoleKey: process.env.SUPABASE_SERVICE_ROLE_KEY ?? localFallback.serviceRoleKey,
  storageUrl,
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL ?? localFallback.supabaseUrl,
});

const supabase = createClient<Database>(env.supabaseUrl, env.serviceRoleKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false,
  },
});
const storageBaseUrl = (env.storageUrl ?? env.supabaseUrl).replace(
  /\/storage\/v1\/?$/,
  ""
);
const storageClient = createClient<Database>(storageBaseUrl, env.serviceRoleKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false,
  },
});

const SEED_PASSWORD = "dev-password-change-me";
const SEED_FIXTURES_DIR = "scripts/seed/fixtures";

const USERS = {
  admin: {
    email: "seed.admin@example.local",
    id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    password: SEED_PASSWORD,
    userMetadata: { full_name: "Seed Admin" },
  },
  calendarUser: {
    email: "seed.calendar@example.local",
    id: "77777777-7777-4777-8777-777777777777",
    password: SEED_PASSWORD,
    userMetadata: { full_name: "Seed Calendar" },
  },
  devCollaborator: {
    email: "dev.collab@example.local",
    id: "22222222-2222-4222-8222-222222222222",
    password: SEED_PASSWORD,
    userMetadata: { full_name: "Dev Collaborator" },
  },
  devOwner: {
    email: "dev.owner@example.local",
    id: "11111111-1111-4111-8111-111111111111",
    password: SEED_PASSWORD,
    userMetadata: { full_name: "Dev Owner" },
  },
  e2eUser: {
    email: "e2e.user@example.local",
    id: "33333333-3333-4333-8333-333333333333",
    password: SEED_PASSWORD,
    userMetadata: { full_name: "E2E User" },
  },
  edgeCaseUser: {
    email: "seed.edge@example.local",
    id: "88888888-8888-4888-8888-888888888888",
    password: SEED_PASSWORD,
    userMetadata: { full_name: "Seed Edge Cases" },
  },
  paymentsUser: {
    email: "seed.payments@example.local",
    id: "66666666-6666-4666-8666-666666666666",
    password: SEED_PASSWORD,
    userMetadata: { full_name: "Seed Payments" },
  },
} as const;

const GATEWAY_TEXT_EMBEDDING_MODEL_ID = "openai/text-embedding-3-small" as const;
const OPENAI_TEXT_EMBEDDING_MODEL_ID = "text-embedding-3-small" as const;
const STORAGE_BUCKETS = [
  {
    allowedMimeTypes: [
      "application/pdf",
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "application/vnd.ms-excel",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "text/plain",
      "text/csv",
      "image/jpeg",
      "image/png",
      "image/gif",
      "image/webp",
      "image/svg+xml",
    ],
    fileSizeLimit: 52_428_800,
    name: "attachments",
    public: false,
  },
  {
    allowedMimeTypes: [
      "image/jpeg",
      "image/png",
      "image/gif",
      "image/webp",
      "image/avif",
    ],
    fileSizeLimit: 5_242_880,
    name: "avatars",
    public: true,
  },
  {
    allowedMimeTypes: [
      "image/jpeg",
      "image/png",
      "image/gif",
      "image/webp",
      "image/avif",
      "image/heic",
      "image/heif",
    ],
    fileSizeLimit: 20_971_520,
    name: "trip-images",
    public: false,
  },
] as const;

function stableUuid(seed: string): string {
  const bytes = createHash("sha256").update(seed).digest().subarray(0, 16);
  // RFC 4122 v4 + variant
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Buffer.from(bytes).toString("hex");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(
    16,
    20
  )}-${hex.slice(20)}`;
}

// Intentionally duplicates src/lib/rag/pgvector.ts (and mirrors the
// TEXT_EMBEDDING_DIMENSIONS duplication) to keep the seed script self-contained,
// avoid server-only imports, and prevent runtime/import issues during seeding.
// Keep this in sync with pgvector helpers to ease maintenance.
function serializePgvector(embedding: readonly number[]): string {
  const parts = embedding.map((value, idx) => {
    if (!Number.isFinite(value)) {
      throw new Error(`Invalid embedding value at index ${idx}`);
    }
    return String(value);
  });
  return `[${parts.join(",")}]`;
}

function getSeedTextEmbeddingModelId(): string {
  if (process.env.AI_GATEWAY_API_KEY) return GATEWAY_TEXT_EMBEDDING_MODEL_ID;
  if (process.env.OPENAI_API_KEY) return OPENAI_TEXT_EMBEDDING_MODEL_ID;
  return DETERMINISTIC_TEXT_EMBEDDING_MODEL_ID;
}

async function embedTextValues(values: string[]): Promise<{
  embeddings: readonly number[][];
  modelId: string;
}> {
  if (values.length === 0) {
    return { embeddings: [], modelId: getSeedTextEmbeddingModelId() };
  }

  const modelId = getSeedTextEmbeddingModelId();
  if (modelId === DETERMINISTIC_TEXT_EMBEDDING_MODEL_ID) {
    return { embeddings: values.map(deterministicTextEmbedding), modelId };
  }

  const model =
    modelId === GATEWAY_TEXT_EMBEDDING_MODEL_ID
      ? modelId
      : openai.embeddingModel(OPENAI_TEXT_EMBEDDING_MODEL_ID);

  const { embeddings } = await embedMany({
    abortSignal: AbortSignal.timeout(20_000),
    maxRetries: 2,
    model,
    values,
  });

  if (embeddings.length !== values.length) {
    throw new Error(
      `Embedding provider returned unexpected length (expected ${values.length}, got ${embeddings.length})`
    );
  }

  for (const [idx, embedding] of embeddings.entries()) {
    if (embedding.length !== TEXT_EMBEDDING_DIMENSIONS) {
      throw new Error(
        `Invalid embedding dimensions at index ${idx} (expected ${TEXT_EMBEDDING_DIMENSIONS}, got ${embedding.length})`
      );
    }
  }

  return { embeddings, modelId };
}

async function ensureStorageBuckets(): Promise<void> {
  for (const bucket of STORAGE_BUCKETS) {
    const { data, error } = await storageClient.storage.getBucket(bucket.name);
    if (data) continue;
    if (error) {
      const status =
        typeof error === "object" && error && "status" in error
          ? Number((error as { status?: number }).status)
          : undefined;
      const message = error instanceof Error ? error.message : String(error);
      const isNotFound = status === 404 || message.toLowerCase().includes("not found");
      if (isNotFound) {
        const { error: createError } = await storageClient.storage.createBucket(
          bucket.name,
          {
            allowedMimeTypes: [...bucket.allowedMimeTypes],
            fileSizeLimit: bucket.fileSizeLimit,
            public: bucket.public,
          }
        );
        if (!createError) {
          continue;
        }
        throw new Error(`createBucket failed (${bucket.name}): ${createError.message}`);
      } else {
        throw new Error(`getBucket failed (${bucket.name}): ${message}`);
      }
    }
    throw new Error(`getBucket failed (${bucket.name}): missing data and error`);
  }
}

async function waitForPostgrestReady(): Promise<void> {
  const maxAttempts = 12;
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    let failureDetail: string | null = null;
    try {
      const res = await fetch(`${env.supabaseUrl}/rest/v1/`, {
        headers: {
          Authorization: `Bearer ${env.serviceRoleKey}`,
          apikey: env.serviceRoleKey,
        },
        method: "GET",
        signal: AbortSignal.timeout(5000),
      });
      if (res.ok) return;
      failureDetail = `${res.status} ${res.statusText}`.trim();
    } catch (error) {
      failureDetail = error instanceof Error ? error.message : String(error);
    }
    if (attempt === maxAttempts) {
      throw new Error(
        `Supabase REST health failed (${failureDetail ?? "unknown"}). Is PostgREST ready?`
      );
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
}

/**
 * Serialize embedding to pgvector format with strict dimension validation.
 *
 * Enforces standard embedding dimensions before serializing to pgvector format.
 */
function toPgvector(embedding: readonly number[]): string {
  if (embedding.length !== TEXT_EMBEDDING_DIMENSIONS) {
    throw new Error(
      `Invalid embedding dimensions (expected ${TEXT_EMBEDDING_DIMENSIONS}, got ${embedding.length})`
    );
  }
  return serializePgvector(embedding);
}

function chunkText(
  text: string,
  chunkSizeTokens: number,
  overlapTokens: number
): string[] {
  const charsPerToken = 4;
  const chunkChars = chunkSizeTokens * charsPerToken;
  const overlapChars = overlapTokens * charsPerToken;

  const trimmed = text.trim();
  if (trimmed.length === 0) return [];
  if (trimmed.length <= chunkChars) return [trimmed];

  const chunks: string[] = [];
  let start = 0;

  while (start < trimmed.length) {
    let end = Math.min(start + chunkChars, trimmed.length);
    if (end < trimmed.length) {
      const searchStart = Math.max(start + chunkChars - 200, start);
      const searchEnd = Math.min(start + chunkChars + 100, trimmed.length);
      const searchText = trimmed.slice(searchStart, searchEnd);
      const sentenceBreaks = [". ", "! ", "? ", ".\n", "!\n", "?\n"];
      let bestBreak = -1;
      for (const br of sentenceBreaks) {
        const idx = searchText.lastIndexOf(br);
        if (idx !== -1) {
          const absoluteIdx = searchStart + idx + br.length;
          if (absoluteIdx > start && absoluteIdx <= start + chunkChars + 50) {
            if (bestBreak === -1 || absoluteIdx > bestBreak) bestBreak = absoluteIdx;
          }
        }
      }
      if (bestBreak !== -1) end = bestBreak;
    }

    const chunk = trimmed.slice(start, end).trim();
    if (chunk.length > 0) chunks.push(chunk);

    const newStart = end - overlapChars;
    start = newStart <= start ? end : newStart;
    if (start >= trimmed.length) break;
  }

  return chunks;
}

const fixtureCache = new Map<string, Buffer>();

async function readFixture(name: string): Promise<Buffer> {
  const cached = fixtureCache.get(name);
  if (cached) return cached;
  const data = await readFile(`${SEED_FIXTURES_DIR}/${name}`);
  fixtureCache.set(name, data);
  return data;
}

async function getUserIdByEmail(email: string): Promise<string | null> {
  const normalizedEmail = email.toLowerCase();
  let page = 1;
  const perPage = 200;

  while (true) {
    const { data, error } = await supabase.auth.admin.listUsers({
      page,
      perPage,
    });
    if (error) throw new Error(`auth.admin.listUsers failed: ${error.message}`);

    const match = data.users.find(
      (u) => (u.email ?? "").toLowerCase() === normalizedEmail
    );
    if (match) return match.id;

    if (!data.nextPage || data.users.length < perPage) return null;
    page = data.nextPage;
  }
}

async function ensureUser(input: {
  id: string;
  email: string;
  password: string;
  userMetadata: Record<string, unknown>;
}): Promise<string> {
  const existingId = await getUserIdByEmail(input.email);
  if (existingId) {
    if (existingId !== input.id) {
      const deleted = await supabase.auth.admin.deleteUser(existingId);
      if (deleted.error) {
        throw new Error(
          `auth.admin.deleteUser failed for ${input.email}: ${deleted.error.message}`
        );
      }
    } else {
      const update = await supabase.auth.admin.updateUserById(existingId, {
        email_confirm: true,
        password: input.password,
        user_metadata: input.userMetadata,
      });
      if (update.error) {
        throw new Error(
          `auth.admin.updateUserById failed for ${input.email}: ${update.error.message}`
        );
      }
      return existingId;
    }
  }

  const created = await supabase.auth.admin.createUser({
    email: input.email,
    email_confirm: true,
    id: input.id,
    password: input.password,
    user_metadata: input.userMetadata,
  });

  if (created.error) {
    throw new Error(
      `auth.admin.createUser failed for ${input.email}: ${created.error.message}`
    );
  }
  if (!created.data.user) {
    throw new Error(`auth.admin.createUser failed for ${input.email}: missing user`);
  }
  return created.data.user.id;
}

async function ensureProfileRow(input: {
  avatarUrl: string | null;
  fullName: string;
  isAdmin?: boolean;
  userId: string;
}): Promise<void> {
  const upsert = await supabase.from("profiles").upsert({
    avatar_url: input.avatarUrl,
    full_name: input.fullName,
    id: input.userId,
    is_admin: input.isAdmin ?? false,
  });
  if (upsert.error) {
    throw new Error(`upsert profiles failed: ${upsert.error.message}`);
  }
}

async function ensureAvatarForUser(input: {
  profile: SeedProfile;
  userId: string;
}): Promise<string> {
  const avatar = await readFixture("avatar.png");
  const objectPath = `seed/${input.profile}/${input.userId}.png`;

  const upload = await storageClient.storage
    .from("avatars")
    .upload(objectPath, new Blob([new Uint8Array(avatar)], { type: "image/png" }), {
      contentType: "image/png",
      upsert: true,
    });
  if (upload.error) {
    throw new Error(`upload avatar failed: ${upload.error.message}`);
  }

  const { data } = storageClient.storage.from("avatars").getPublicUrl(objectPath);
  if (!data.publicUrl) {
    throw new Error("getPublicUrl failed: missing publicUrl");
  }
  return data.publicUrl;
}

async function ensureUserWithProfile(input: {
  isAdmin?: boolean;
  profile: SeedProfile;
  user: (typeof USERS)[keyof typeof USERS];
}): Promise<string> {
  const userId = await ensureUser(input.user);
  const avatarUrl = await ensureAvatarForUser({ profile: input.profile, userId });

  const mergedMetadata = {
    ...input.user.userMetadata,
    avatar_url: avatarUrl,
  };
  const update = await supabase.auth.admin.updateUserById(userId, {
    email_confirm: true,
    user_metadata: mergedMetadata,
  });
  if (update.error) {
    throw new Error(`auth.admin.updateUserById failed for ${input.user.email}`);
  }

  await ensureProfileRow({
    avatarUrl,
    fullName: String(input.user.userMetadata.full_name ?? "Seed User"),
    isAdmin: input.isAdmin,
    userId,
  });

  return userId;
}

async function ensureTrip(input: {
  userId: string;
  name: string;
  destination: string;
  startDate: string; // YYYY-MM-DD
  endDate: string; // YYYY-MM-DD
  travelers: number;
  description?: string;
}): Promise<number> {
  const existing = await supabase
    .from("trips")
    .select("id")
    .eq("user_id", input.userId)
    .eq("name", input.name)
    .maybeSingle();
  if (existing.error) {
    throw new Error(`select trip failed for ${input.name}: ${existing.error.message}`);
  }

  if (existing.data?.id) {
    const updated = await supabase
      .from("trips")
      .update({
        description: input.description ?? null,
        destination: input.destination,
        end_date: input.endDate,
        start_date: input.startDate,
        travelers: input.travelers,
      })
      .eq("id", existing.data.id)
      .select("id")
      .single();

    if (updated.error) {
      throw new Error(`update trip failed for ${input.name}: ${updated.error.message}`);
    }
    if (!updated.data) {
      throw new Error(`update trip failed for ${input.name}: missing data`);
    }
    return updated.data.id;
  }

  const created = await supabase
    .from("trips")
    .insert({
      budget: 1500,
      currency: "USD",
      description: input.description ?? null,
      destination: input.destination,
      end_date: input.endDate,
      flexibility: null,
      name: input.name,
      search_metadata: null,
      start_date: input.startDate,
      status: "planning",
      tags: ["seed"],
      travelers: input.travelers,
      trip_type: "leisure",
      user_id: input.userId,
    })
    .select("id")
    .single();

  if (created.error) {
    throw new Error(`insert trip failed for ${input.name}: ${created.error.message}`);
  }
  if (!created.data) {
    throw new Error(`insert trip failed for ${input.name}: missing data`);
  }
  return created.data.id;
}

async function ensureTripCollaborator(input: {
  tripId: number;
  userId: string;
  role: string;
}): Promise<void> {
  const existing = await supabase
    .from("trip_collaborators")
    .select("id, role")
    .eq("trip_id", input.tripId)
    .eq("user_id", input.userId)
    .maybeSingle();
  if (existing.error) {
    throw new Error(`select trip_collaborators failed: ${existing.error.message}`);
  }

  if (existing.data?.id) {
    if (existing.data.role === input.role) return;
    const updated = await supabase
      .from("trip_collaborators")
      .update({ role: input.role })
      .eq("id", existing.data.id);
    if (updated.error) {
      throw new Error(`update trip_collaborators failed: ${updated.error.message}`);
    }
    return;
  }

  const inserted = await supabase.from("trip_collaborators").insert({
    role: input.role,
    trip_id: input.tripId,
    user_id: input.userId,
  });
  if (inserted.error) {
    throw new Error(`insert trip_collaborators failed: ${inserted.error.message}`);
  }
}

async function resetSeededItinerary(tripId: number): Promise<void> {
  const deleted = await supabase
    .from("itinerary_items")
    .delete()
    .eq("trip_id", tripId)
    .like("external_id", "seed:%");
  if (deleted.error) {
    throw new Error(`delete itinerary_items failed: ${deleted.error.message}`);
  }
}

async function seedItineraryItems(input: {
  tripId: number;
  userId: string;
  items: Array<{
    externalId: string;
    itemType: string;
    title: string;
    startTime?: string;
    endTime?: string;
    location?: string;
    description?: string;
    metadata?: Json;
  }>;
}): Promise<void> {
  await resetSeededItinerary(input.tripId);
  if (input.items.length === 0) return;

  const inserted = await supabase.from("itinerary_items").insert(
    input.items.map((item) => ({
      description: item.description ?? null,
      end_time: item.endTime ?? null,
      external_id: item.externalId,
      item_type: item.itemType,
      location: item.location ?? null,
      metadata: item.metadata ?? null,
      start_time: item.startTime ?? null,
      title: item.title,
      trip_id: input.tripId,
      user_id: input.userId,
    }))
  );
  if (inserted.error) {
    throw new Error(`insert itinerary_items failed: ${inserted.error.message}`);
  }
}

async function seedSavedPlaces(input: {
  tripId: number;
  userId: string;
  places: Array<{ placeId: string; provider: string; snapshot: Json }>;
}): Promise<void> {
  const deleted = await supabase
    .from("saved_places")
    .delete()
    .eq("trip_id", input.tripId)
    .eq("user_id", input.userId)
    .like("place_id", "seed-%");
  if (deleted.error) {
    throw new Error(`delete saved_places failed: ${deleted.error.message}`);
  }

  if (input.places.length === 0) return;
  const inserted = await supabase.from("saved_places").insert(
    input.places.map((place) => ({
      place_id: place.placeId,
      place_snapshot: place.snapshot,
      provider: place.provider,
      trip_id: input.tripId,
      user_id: input.userId,
    }))
  );
  if (inserted.error) {
    throw new Error(`insert saved_places failed: ${inserted.error.message}`);
  }
}

async function seedChatSession(input: {
  sessionId: string;
  tripId: number;
  userId: string;
  messages: Array<{ role: string; content: string }>;
}): Promise<{ messageIds: number[] }> {
  const sessionUpsert = await supabase.from("chat_sessions").upsert({
    id: input.sessionId,
    metadata: { source: "seed" },
    trip_id: input.tripId,
    user_id: input.userId,
  });
  if (sessionUpsert.error) {
    throw new Error(`upsert chat_sessions failed: ${sessionUpsert.error.message}`);
  }

  const deleted = await supabase
    .from("chat_messages")
    .delete()
    .eq("session_id", input.sessionId);
  if (deleted.error) {
    throw new Error(`delete chat_messages failed: ${deleted.error.message}`);
  }

  if (input.messages.length === 0) return { messageIds: [] };
  const inserted = await supabase
    .from("chat_messages")
    .insert(
      input.messages.map((msg) => ({
        content: msg.content,
        metadata: { source: "seed" },
        role: msg.role,
        session_id: input.sessionId,
        user_id: input.userId,
      }))
    )
    .select("id");
  if (inserted.error) {
    throw new Error(`insert chat_messages failed: ${inserted.error.message}`);
  }
  const messageIds = (inserted.data ?? []).map((row) => row.id);
  return { messageIds };
}

async function resetByIds(params: {
  ids: string[];
  table: keyof Database["public"]["Tables"];
}): Promise<void> {
  if (params.ids.length === 0) return;
  const deleted = await supabase.from(params.table).delete().in("id", params.ids);
  if (deleted.error) {
    throw new Error(`delete ${params.table} failed: ${deleted.error.message}`);
  }
}

async function seedApiMetrics(input: {
  userId: string;
  metrics: Array<{
    durationMs: number;
    endpoint: string;
    id: string;
    method: string;
    rateLimitKey?: string | null;
    statusCode: number;
  }>;
}): Promise<void> {
  await resetByIds({
    ids: input.metrics.map((m) => m.id),
    table: "api_metrics",
  });

  const inserted = await supabase.from("api_metrics").insert(
    input.metrics.map((m) => ({
      duration_ms: m.durationMs,
      endpoint: m.endpoint,
      id: m.id,
      method: m.method,
      rate_limit_key: m.rateLimitKey ?? null,
      status_code: m.statusCode,
      user_id: input.userId,
    }))
  );
  if (inserted.error) {
    throw new Error(`insert api_metrics failed: ${inserted.error.message}`);
  }
}

async function seedSearchDestinations(input: {
  userId: string;
  rows: Array<{
    expiresAt: string;
    query: string;
    queryHash: string;
    results: Json;
    source: "google_maps" | "external_api" | "cached";
  }>;
}): Promise<void> {
  if (input.rows.length === 0) return;
  const deleted = await supabase
    .from("search_destinations")
    .delete()
    .eq("user_id", input.userId)
    .in(
      "query_hash",
      input.rows.map((row) => row.queryHash)
    );
  if (deleted.error) {
    throw new Error(`delete search_destinations failed: ${deleted.error.message}`);
  }

  const inserted = await supabase.from("search_destinations").insert(
    input.rows.map((row) => ({
      expires_at: row.expiresAt,
      query: row.query,
      query_hash: row.queryHash,
      results: row.results,
      search_metadata: { source: "seed" },
      source: row.source,
      user_id: input.userId,
    }))
  );
  if (inserted.error) {
    throw new Error(`insert search_destinations failed: ${inserted.error.message}`);
  }
}

async function extractTextFromAttachment(params: {
  buffer: Buffer;
  mimeType: string;
  originalFilename: string;
}): Promise<string | null> {
  switch (params.mimeType) {
    case "text/plain":
    case "text/csv":
      return params.buffer.toString("utf8");

    case "application/pdf": {
      const pdfParsePkg = await import("pdf-parse");
      const { PDFParse } = pdfParsePkg;
      const parser = new PDFParse({ data: params.buffer });
      const parsed = await parser.getText({ first: 10 });
      return parsed.text;
    }

    case "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
      const mammoth = await import("mammoth");
      const parsed = await mammoth.extractRawText({ buffer: params.buffer });
      return parsed.value;
    }

    default:
      return null;
  }
}

async function seedAttachmentAndRag(params: {
  attachmentId: string;
  chatId: string;
  chatMessageId: number;
  fileName: string;
  mimeType: string;
  originalFilename: string;
  profile: SeedProfile;
  tripId: number;
  userId: string;
}): Promise<void> {
  const buffer = await readFixture(params.fileName);
  const filePath = `${params.userId}/${params.tripId}/${params.chatId}/${params.attachmentId}/${basename(
    params.originalFilename
  )}`;

  // Create metadata row first (mirrors metadata-first upload flow).
  const upsertAttachment = await supabase.from("file_attachments").upsert({
    bucket_name: "attachments",
    chat_id: params.chatId,
    chat_message_id: params.chatMessageId,
    file_path: filePath,
    file_size: buffer.byteLength,
    filename: basename(params.originalFilename),
    id: params.attachmentId,
    metadata: { profile: params.profile, source: "seed" },
    mime_type: params.mimeType,
    original_filename: params.originalFilename,
    trip_id: params.tripId,
    upload_status: "uploading",
    user_id: params.userId,
    virus_scan_result: {},
    virus_scan_status: "pending",
  });
  if (upsertAttachment.error) {
    throw new Error(
      `upsert file_attachments failed: ${upsertAttachment.error.message}`
    );
  }

  const upload = await storageClient.storage
    .from("attachments")
    .upload(filePath, new Blob([new Uint8Array(buffer)], { type: params.mimeType }), {
      contentType: params.mimeType,
      upsert: true,
    });
  if (upload.error) {
    throw new Error(`upload attachment failed: ${upload.error.message}`);
  }

  const finalize = await supabase
    .from("file_attachments")
    .update({ upload_status: "completed", virus_scan_status: "clean" })
    .eq("id", params.attachmentId);
  if (finalize.error) {
    throw new Error(`finalize file_attachments failed: ${finalize.error.message}`);
  }

  const extracted = await extractTextFromAttachment({
    buffer,
    mimeType: params.mimeType,
    originalFilename: params.originalFilename,
  });
  if (!extracted) return;

  const chunks = chunkText(extracted, 512, 100);
  if (chunks.length === 0) return;

  const { embeddings, modelId } = await embedTextValues(chunks);
  const ragRows = chunks.map((content, idx) => {
    const embedding = embeddings[idx];
    if (!embedding) throw new Error(`Missing embedding for chunk index ${idx}`);
    return {
      chat_id: params.chatId,
      chunk_index: idx,
      content,
      embedding: toPgvector(embedding),
      id: params.attachmentId,
      metadata: {
        attachmentId: params.attachmentId,
        embeddingModel: modelId,
        filePath,
        mimeType: params.mimeType,
        originalFilename: params.originalFilename,
        profile: params.profile,
        source: "seed",
      },
      namespace: "user_content",
      source_id: params.attachmentId,
      trip_id: params.tripId,
      user_id: params.userId,
    };
  });

  const upsertRag = await supabase
    .from("rag_documents")
    .upsert(ragRows, { onConflict: "id,chunk_index" });
  if (upsertRag.error) {
    throw new Error(`upsert rag_documents failed: ${upsertRag.error.message}`);
  }
}

async function seedMemorySession(params: {
  profile: SeedProfile;
  sessionId: string;
  title: string;
  turns: Array<{ id: string; role: "user" | "assistant"; text: string }>;
  userId: string;
}): Promise<void> {
  const upsertSession = await supabase
    .schema("memories")
    .from("sessions")
    .upsert({
      id: params.sessionId,
      metadata: { profile: params.profile, source: "seed" },
      title: params.title,
      user_id: params.userId,
    });
  if (upsertSession.error) {
    throw new Error(`upsert memories.sessions failed: ${upsertSession.error.message}`);
  }

  const deletedTurns = await supabase
    .schema("memories")
    .from("turns")
    .delete()
    .eq("session_id", params.sessionId);
  if (deletedTurns.error) {
    throw new Error(`delete memories.turns failed: ${deletedTurns.error.message}`);
  }

  const insertedTurns = await supabase
    .schema("memories")
    .from("turns")
    .insert(
      params.turns.map((t) => ({
        attachments: [],
        content: { text: t.text },
        id: t.id,
        pii_scrubbed: true,
        role: t.role,
        session_id: params.sessionId,
        tool_calls: [],
        tool_results: [],
        user_id: params.userId,
      }))
    );
  if (insertedTurns.error) {
    throw new Error(`insert memories.turns failed: ${insertedTurns.error.message}`);
  }

  const { embeddings, modelId } = await embedTextValues(
    params.turns.map((t) => t.text)
  );
  const embeddingsRows = params.turns.map((t, idx) => {
    const embedding = embeddings[idx];
    if (!embedding) throw new Error(`Missing embedding for turn index ${idx}`);
    return {
      embedding: toPgvector(embedding),
      model: modelId,
      turn_id: t.id,
    };
  });

  const upsertEmbeddings = await supabase
    .schema("memories")
    .from("turn_embeddings")
    .upsert(embeddingsRows, { onConflict: "turn_id" });
  if (upsertEmbeddings.error) {
    throw new Error(
      `upsert memories.turn_embeddings failed: ${upsertEmbeddings.error.message}`
    );
  }
}

async function seedWebhooks(params: { profile: SeedProfile }): Promise<void> {
  const configId = stableUuid(`seed:${params.profile}:webhook_config`);
  const eventId = stableUuid(`seed:${params.profile}:webhook_event`);

  const upsertConfig = await supabase.from("webhook_configs").upsert({
    enabled: true,
    endpoint: "https://example.local/webhooks/seed",
    id: configId,
    name: `Seed Webhook (${params.profile})`,
    secret: "seed-secret",
  });
  if (upsertConfig.error) {
    throw new Error(`upsert webhook_configs failed: ${upsertConfig.error.message}`);
  }

  const upsertEvent = await supabase.from("webhook_events").upsert({
    config_id: configId,
    delivery_status: "failed",
    event_type: "seed.test",
    id: eventId,
    last_error: "seed delivery failed (intentional)",
    payload: { profile: params.profile, seed: true },
  });
  if (upsertEvent.error) {
    throw new Error(`upsert webhook_events failed: ${upsertEvent.error.message}`);
  }

  const deletedLogs = await supabase
    .from("webhook_logs")
    .delete()
    .eq("event_id", eventId);
  if (deletedLogs.error) {
    throw new Error(`delete webhook_logs failed: ${deletedLogs.error.message}`);
  }

  const insertLog = await supabase.from("webhook_logs").insert({
    attempt_number: 1,
    event_id: eventId,
    response_body: "seed webhook endpoint unreachable",
    status_code: 502,
  });
  if (insertLog.error) {
    throw new Error(`insert webhook_logs failed: ${insertLog.error.message}`);
  }
}

async function seedInboundWebhookReceipts(params: {
  profile: SeedProfile;
}): Promise<void> {
  const body = `seed:${params.profile}:inbound_webhook_receipt`;
  const bodySha = createHash("sha256").update(body, "utf8").digest("hex");
  const id = stableUuid(`seed:${params.profile}:inbound_webhook_receipt`);

  await resetByIds({ ids: [id], table: "inbound_webhook_receipts" });
  const inserted = await supabase.from("inbound_webhook_receipts").insert({
    body_sha256: bodySha,
    handler: "seed",
    headers_subset: { "content-type": "application/json" },
    id,
    idempotency_key: `seed:${params.profile}:idem`,
    request_id: `seed:${params.profile}:req`,
    result_status: 200,
    signature_valid: true,
    source: "other",
  });
  if (inserted.error) {
    throw new Error(
      `insert inbound_webhook_receipts failed: ${inserted.error.message}`
    );
  }
}

async function runDevSeed(): Promise<void> {
  await ensureUserWithProfile({
    isAdmin: true,
    profile: "dev",
    user: USERS.admin,
  });
  const ownerId = await ensureUserWithProfile({ profile: "dev", user: USERS.devOwner });
  const collaboratorId = await ensureUserWithProfile({
    profile: "dev",
    user: USERS.devCollaborator,
  });

  const tripId = await ensureTrip({
    description: "Seeded trip for local development.",
    destination: "San Francisco, CA",
    endDate: "2026-06-05",
    name: "Dev Seed Trip",
    startDate: "2026-06-01",
    travelers: 2,
    userId: ownerId,
  });

  await ensureTripCollaborator({
    role: "editor",
    tripId,
    userId: collaboratorId,
  });

  await seedItineraryItems({
    items: [
      {
        endTime: "2026-06-01T10:00:00+00:00",
        externalId: "seed:itinerary:coffee",
        itemType: "meal",
        location: "Mission District",
        startTime: "2026-06-01T09:00:00+00:00",
        title: "Coffee and pastries",
      },
      {
        endTime: "2026-06-01T18:00:00+00:00",
        externalId: "seed:itinerary:golden-gate",
        itemType: "activity",
        location: "Golden Gate Bridge",
        startTime: "2026-06-01T16:00:00+00:00",
        title: "Golden Gate Bridge",
      },
    ],
    tripId,
    userId: ownerId,
  });

  await seedSavedPlaces({
    places: [
      {
        placeId: "seed-place-golden-gate",
        provider: "google_places",
        snapshot: {
          formattedAddress: "Golden Gate Bridge, San Francisco, CA",
          name: "Golden Gate Bridge",
          source: "seed",
          types: ["tourist_attraction"],
        },
      },
    ],
    tripId,
    userId: ownerId,
  });

  const devChat = await seedChatSession({
    messages: [
      { content: "Plan a 4-day SF itinerary focused on food.", role: "user" },
      { content: "Here’s a structured 4-day plan you can refine…", role: "assistant" },
    ],
    sessionId: "44444444-4444-4444-4444-444444444444",
    tripId,
    userId: ownerId,
  });

  const [firstMessageId] = devChat.messageIds;
  if (!firstMessageId) {
    throw new Error("seedChatSession failed: missing message ids");
  }

  const deletedToolCalls = await supabase
    .from("chat_tool_calls")
    .delete()
    .in("message_id", devChat.messageIds);
  if (deletedToolCalls.error) {
    throw new Error(`delete chat_tool_calls failed: ${deletedToolCalls.error.message}`);
  }

  const insertedToolCall = await supabase.from("chat_tool_calls").insert({
    arguments: { days: 4, destination: "San Francisco, CA", source: "seed" },
    message_id: devChat.messageIds[1] ?? firstMessageId,
    result: { ok: true, source: "seed" },
    status: "completed",
    tool_id: "seed-tool-1",
    tool_name: "plan_trip",
  });
  if (insertedToolCall.error) {
    throw new Error(`insert chat_tool_calls failed: ${insertedToolCall.error.message}`);
  }

  await seedAttachmentAndRag({
    attachmentId: stableUuid("seed:dev:attachment:hello_txt"),
    chatId: "44444444-4444-4444-4444-444444444444",
    chatMessageId: firstMessageId,
    fileName: "hello.txt",
    mimeType: "text/plain",
    originalFilename: "hello.txt",
    profile: "dev",
    tripId,
    userId: ownerId,
  });

  await seedAttachmentAndRag({
    attachmentId: stableUuid("seed:dev:attachment:sample_csv"),
    chatId: "44444444-4444-4444-4444-444444444444",
    chatMessageId: firstMessageId,
    fileName: "sample.csv",
    mimeType: "text/csv",
    originalFilename: "sample.csv",
    profile: "dev",
    tripId,
    userId: ownerId,
  });

  await seedAttachmentAndRag({
    attachmentId: stableUuid("seed:dev:attachment:sample_pdf"),
    chatId: "44444444-4444-4444-4444-444444444444",
    chatMessageId: firstMessageId,
    fileName: "sample.pdf",
    mimeType: "application/pdf",
    originalFilename: "sample.pdf",
    profile: "dev",
    tripId,
    userId: ownerId,
  });

  await seedAttachmentAndRag({
    attachmentId: stableUuid("seed:dev:attachment:sample_docx"),
    chatId: "44444444-4444-4444-4444-444444444444",
    chatMessageId: firstMessageId,
    fileName: "sample.docx",
    mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    originalFilename: "sample.docx",
    profile: "dev",
    tripId,
    userId: ownerId,
  });

  await seedMemorySession({
    profile: "dev",
    sessionId: stableUuid("seed:dev:memories:session"),
    title: "Seed Memory Session (dev)",
    turns: [
      {
        id: stableUuid("seed:dev:memories:turn:user"),
        role: "user",
        text: "Remember: I prefer vegetarian-friendly itineraries and morning flights.",
      },
      {
        id: stableUuid("seed:dev:memories:turn:assistant"),
        role: "assistant",
        text: "Noted. I will prioritize vegetarian options and flights departing before noon.",
      },
    ],
    userId: ownerId,
  });

  await seedWebhooks({ profile: "dev" });
  await seedInboundWebhookReceipts({ profile: "dev" });

  await seedApiMetrics({
    metrics: [
      {
        durationMs: 120,
        endpoint: "/api/trips",
        id: stableUuid("seed:dev:api_metrics:trips_get"),
        method: "GET",
        rateLimitKey: "seed:dev:ratelimit:trips",
        statusCode: 200,
      },
      {
        durationMs: 980,
        endpoint: "/api/chat",
        id: stableUuid("seed:dev:api_metrics:chat_post"),
        method: "POST",
        rateLimitKey: "seed:dev:ratelimit:chat",
        statusCode: 429,
      },
    ],
    userId: ownerId,
  });

  await seedSearchDestinations({
    rows: [
      {
        expiresAt: "2030-01-01T00:00:00+00:00",
        query: "San Francisco",
        queryHash: "seed:dev:destinations:san-francisco",
        results: [
          {
            formattedAddress: "San Francisco, CA, USA",
            name: "San Francisco",
            placeId: "ChIJIQBpAG2ahYAR_6128GcTUEo",
            source: "seed",
          },
        ],
        source: "cached",
      },
    ],
    userId: ownerId,
  });
}

async function runE2eSeed(): Promise<void> {
  const userId = await ensureUserWithProfile({ profile: "e2e", user: USERS.e2eUser });
  const tripId = await ensureTrip({
    description: "Seeded trip for Playwright E2E flows.",
    destination: "New York, NY",
    endDate: "2026-07-12",
    name: "E2E Seed Trip",
    startDate: "2026-07-10",
    travelers: 1,
    userId,
  });

  await seedItineraryItems({
    items: [
      {
        endTime: "2026-07-10T16:00:00+00:00",
        externalId: "seed:e2e:itinerary:walk",
        itemType: "activity",
        location: "Central Park",
        startTime: "2026-07-10T14:00:00+00:00",
        title: "Walk Central Park",
      },
    ],
    tripId,
    userId,
  });

  await seedChatSession({
    messages: [{ content: "Suggest a simple NYC weekend plan.", role: "user" }],
    sessionId: "55555555-5555-5555-5555-555555555555",
    tripId,
    userId,
  });
}

async function runPaymentsSeed(): Promise<void> {
  const userId = await ensureUserWithProfile({
    profile: "payments",
    user: USERS.paymentsUser,
  });

  const tripId = await ensureTrip({
    description: "Seeded trip for payments + bookings flows.",
    destination: "Las Vegas, NV",
    endDate: "2026-08-05",
    name: "Payments Seed Trip",
    startDate: "2026-08-01",
    travelers: 2,
    userId,
  });

  const bookingId = `seed:payments:booking:${stableUuid("seed:payments:booking")}`;
  const upsertBooking = await supabase.from("bookings").upsert({
    checkin: "2026-08-01",
    checkout: "2026-08-05",
    guest_email: "guest@example.local",
    guest_name: "Seed Guest",
    guests: 2,
    id: bookingId,
    property_id: "seed-property-001",
    provider_booking_id: "seed-provider-booking-001",
    status: "confirmed",
    stripe_payment_intent_id: "pi_seed_000000000000000000000000",
    trip_id: tripId,
    user_id: userId,
  });
  if (upsertBooking.error) {
    throw new Error(`upsert bookings failed: ${upsertBooking.error.message}`);
  }

  await seedInboundWebhookReceipts({ profile: "payments" });
  await seedWebhooks({ profile: "payments" });
}

async function runCalendarSeed(): Promise<void> {
  const userId = await ensureUserWithProfile({
    profile: "calendar",
    user: USERS.calendarUser,
  });

  const tripId = await ensureTrip({
    description: "Seeded trip for ICS import/export and calendar views.",
    destination: "Tokyo, JP",
    endDate: "2026-04-12",
    name: "Calendar Seed Trip",
    startDate: "2026-04-05",
    travelers: 1,
    userId,
  });

  await seedItineraryItems({
    items: [
      {
        endTime: "2026-04-06T02:00:00+09:00",
        externalId: "seed:calendar:itinerary:sensoji",
        itemType: "activity",
        location: "Sensō-ji, Asakusa",
        startTime: "2026-04-06T00:30:00+09:00",
        title: "Sensō-ji late-night walk",
      },
      {
        endTime: "2026-04-07T13:00:00+09:00",
        externalId: "seed:calendar:itinerary:sushi",
        itemType: "meal",
        location: "Tsukiji Outer Market",
        startTime: "2026-04-07T11:30:00+09:00",
        title: "Sushi lunch",
      },
    ],
    tripId,
    userId,
  });

  await seedChatSession({
    messages: [
      {
        content:
          "Export my itinerary as an ICS file and include Tokyo timezone if available.",
        role: "user",
      },
    ],
    sessionId: stableUuid("seed:calendar:chat_session"),
    tripId,
    userId,
  });
}

async function runEdgeCasesSeed(): Promise<void> {
  const userId = await ensureUserWithProfile({
    profile: "edge-cases",
    user: USERS.edgeCaseUser,
  });

  const tripId = await ensureTrip({
    description:
      "Edge cases: unicode, long strings, nulls, expired caches, attachment warnings.",
    destination: "Reykjavík, IS — 東京 — São Paulo",
    endDate: "2026-12-20",
    name: "Edge Cases Seed Trip — ✈️",
    startDate: "2026-12-10",
    travelers: 1,
    userId,
  });

  await seedSearchDestinations({
    rows: [
      {
        expiresAt: "2000-01-01T00:00:00+00:00",
        query: "Expired seed cache",
        queryHash: "seed:edge:destinations:expired",
        results: [],
        source: "cached",
      },
    ],
    userId,
  });

  const chat = await seedChatSession({
    messages: [
      {
        content: `Test edge cases: extremely-long-content ${"x".repeat(800)} end.`,
        role: "user",
      },
    ],
    sessionId: stableUuid("seed:edge:chat_session"),
    tripId,
    userId,
  });

  const [msgId] = chat.messageIds;
  if (!msgId) throw new Error("edge-cases chat seed failed: missing message ids");

  // Infected attachment row to exercise "skip infected" logic in ingestion jobs.
  const attachmentId = stableUuid("seed:edge:attachment:infected");
  const buffer = await readFixture("hello.txt");
  const filePath = `${userId}/${tripId}/${stableUuid(
    "seed:edge:chat_session"
  )}/${attachmentId}/infected.txt`;

  const attachmentResult = await supabase.from("file_attachments").upsert({
    bucket_name: "attachments",
    chat_id: stableUuid("seed:edge:chat_session"),
    chat_message_id: msgId,
    file_path: filePath,
    file_size: buffer.byteLength,
    filename: "infected.txt",
    id: attachmentId,
    metadata: { profile: "edge-cases", source: "seed" },
    mime_type: "text/plain",
    original_filename: "infected.txt",
    trip_id: tripId,
    upload_status: "completed",
    user_id: userId,
    virus_scan_result: { reason: "seed infected" },
    virus_scan_status: "infected",
  });

  if (attachmentResult.error) {
    throw new Error(
      `upsert file_attachments (infected) failed: ${attachmentResult.error.message}`
    );
  }
}

async function main(): Promise<void> {
  const { hostname } = new URL(env.supabaseUrl);
  const allowRemote = process.env.SUPABASE_SEED_ALLOW_REMOTE === "true";
  const isLocal =
    hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
  if (!isLocal && !allowRemote) {
    throw new Error(
      `Refusing to seed non-local Supabase (${hostname}). Set SUPABASE_SEED_ALLOW_REMOTE=true to override.`
    );
  }

  // Basic connectivity check to surface obvious misconfiguration early.
  const health = await fetch(`${env.supabaseUrl}/auth/v1/health`, { method: "GET" });
  if (!health.ok) {
    throw new Error(
      `Supabase auth health failed (${health.status} ${health.statusText}). Is local Supabase running?`
    );
  }

  await waitForPostgrestReady();
  await ensureStorageBuckets();

  if (profile === "dev") {
    await runDevSeed();
    console.log(
      [
        "Seed complete (dev).",
        `- user: ${USERS.devOwner.email} / ${SEED_PASSWORD}`,
        `- user: ${USERS.devCollaborator.email} / ${SEED_PASSWORD}`,
        `- user: ${USERS.admin.email} / ${SEED_PASSWORD} (admin)`,
      ].join("\n")
    );
    return;
  }

  if (profile === "e2e") {
    await runE2eSeed();
    console.log(
      [
        "Seed complete (e2e).",
        `- user: ${USERS.e2eUser.email} / ${SEED_PASSWORD}`,
      ].join("\n")
    );
    return;
  }

  if (profile === "payments") {
    await runPaymentsSeed();
    console.log(
      [
        "Seed complete (payments).",
        `- user: ${USERS.paymentsUser.email} / ${SEED_PASSWORD}`,
      ].join("\n")
    );
    return;
  }

  if (profile === "calendar") {
    await runCalendarSeed();
    console.log(
      [
        "Seed complete (calendar).",
        `- user: ${USERS.calendarUser.email} / ${SEED_PASSWORD}`,
      ].join("\n")
    );
    return;
  }

  await runEdgeCasesSeed();
  console.log(
    [
      "Seed complete (edge-cases).",
      `- user: ${USERS.edgeCaseUser.email} / ${SEED_PASSWORD}`,
    ].join("\n")
  );
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`${message}\n`);
  process.exit(1);
});
