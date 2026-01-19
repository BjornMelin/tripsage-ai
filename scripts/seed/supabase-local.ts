#!/usr/bin/env tsx

/**
 * @fileoverview Deterministic local seed data for Supabase (dev + e2e profiles).
 *
 * Usage:
 *   pnpm supabase:seed:dev
 *   pnpm supabase:seed:e2e
 *
 * Requirements:
 * - NEXT_PUBLIC_SUPABASE_URL (local or remote)
 * - SUPABASE_SERVICE_ROLE_KEY (server-only; never expose client-side)
 */

// biome-ignore-all lint/style/useNamingConvention: Supabase APIs and DB columns require snake_case keys.

import { createClient } from "@supabase/supabase-js";
import { z } from "zod";
import type { Database, Json } from "../../src/lib/supabase/database.types";

type SeedProfile = "dev" | "e2e";

const envSchema = z.object({
  serviceRoleKey: z.string().min(1),
  supabaseUrl: z.string().url(),
});

const argvProfile = process.argv
  .find((arg) => arg.startsWith("--profile="))
  ?.slice("--profile=".length);

const profile: SeedProfile =
  argvProfile === "e2e" || argvProfile === "dev" ? argvProfile : "dev";

const env = envSchema.parse({
  serviceRoleKey: process.env.SUPABASE_SERVICE_ROLE_KEY,
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL,
});

const supabase = createClient<Database>(env.supabaseUrl, env.serviceRoleKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false,
  },
});

const SEED_PASSWORD = "dev-password-change-me";

const USERS = {
  devCollaborator: {
    email: "dev.collab@example.local",
    id: "22222222-2222-2222-2222-222222222222",
    password: SEED_PASSWORD,
    userMetadata: { name: "Dev Collaborator" },
  },
  devOwner: {
    email: "dev.owner@example.local",
    id: "11111111-1111-1111-1111-111111111111",
    password: SEED_PASSWORD,
    userMetadata: { name: "Dev Owner" },
  },
  e2eUser: {
    email: "e2e.user@example.local",
    id: "33333333-3333-3333-3333-333333333333",
    password: SEED_PASSWORD,
    userMetadata: { name: "E2E User" },
  },
} as const;

async function getUserIdByEmail(email: string): Promise<string | null> {
  const { data, error } = await supabase.auth.admin.listUsers();
  if (error) throw new Error("auth.admin.listUsers failed");

  const users = data.users;
  const match = users.find(
    (u) => (u.email ?? "").toLowerCase() === email.toLowerCase()
  );
  return match?.id ?? null;
}

async function ensureUser(input: {
  id: string;
  email: string;
  password: string;
  userMetadata: Record<string, unknown>;
}): Promise<string> {
  const existingId = await getUserIdByEmail(input.email);
  if (existingId) {
    const update = await supabase.auth.admin.updateUserById(existingId, {
      email_confirm: true,
      password: input.password,
      user_metadata: input.userMetadata,
    });
    if (update.error) {
      throw new Error(`auth.admin.updateUserById failed for ${input.email}`);
    }
    return existingId;
  }

  const created = await supabase.auth.admin.createUser({
    email: input.email,
    email_confirm: true,
    id: input.id,
    password: input.password,
    user_metadata: input.userMetadata,
  });

  if (created.error || !created.data.user) {
    throw new Error(`auth.admin.createUser failed for ${input.email}`);
  }
  return created.data.user.id;
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

    if (updated.error || !updated.data) {
      throw new Error(`update trip failed for ${input.name}`);
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

  if (created.error || !created.data) {
    throw new Error(`insert trip failed for ${input.name}`);
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

  if (existing.data?.id) {
    if (existing.data.role === input.role) return;
    const updated = await supabase
      .from("trip_collaborators")
      .update({ role: input.role })
      .eq("id", existing.data.id);
    if (updated.error) throw new Error("update trip_collaborators failed");
    return;
  }

  const inserted = await supabase.from("trip_collaborators").insert({
    role: input.role,
    trip_id: input.tripId,
    user_id: input.userId,
  });
  if (inserted.error) throw new Error("insert trip_collaborators failed");
}

async function resetSeededItinerary(tripId: number): Promise<void> {
  const deleted = await supabase
    .from("itinerary_items")
    .delete()
    .eq("trip_id", tripId)
    .like("external_id", "seed:%");
  if (deleted.error) throw new Error("delete itinerary_items failed");
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
  if (inserted.error) throw new Error("insert itinerary_items failed");
}

async function seedSavedPlaces(input: {
  tripId: number;
  userId: string;
  places: Array<{ placeId: string; provider: string; snapshot: Json }>;
}): Promise<void> {
  for (const place of input.places) {
    const deleted = await supabase
      .from("saved_places")
      .delete()
      .eq("trip_id", input.tripId)
      .eq("place_id", place.placeId);
    if (deleted.error) throw new Error("delete saved_places failed");
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
  if (inserted.error) throw new Error("insert saved_places failed");
}

async function seedChatSession(input: {
  sessionId: string;
  tripId: number;
  userId: string;
  messages: Array<{ role: string; content: string }>;
}): Promise<void> {
  const sessionUpsert = await supabase.from("chat_sessions").upsert({
    id: input.sessionId,
    metadata: { source: "seed" },
    trip_id: input.tripId,
    user_id: input.userId,
  });
  if (sessionUpsert.error) throw new Error("upsert chat_sessions failed");

  const deleted = await supabase
    .from("chat_messages")
    .delete()
    .eq("session_id", input.sessionId);
  if (deleted.error) throw new Error("delete chat_messages failed");

  if (input.messages.length === 0) return;
  const inserted = await supabase.from("chat_messages").insert(
    input.messages.map((msg) => ({
      content: msg.content,
      role: msg.role,
      session_id: input.sessionId,
      user_id: input.userId,
    }))
  );
  if (inserted.error) throw new Error("insert chat_messages failed");
}

async function runDevSeed(): Promise<void> {
  const ownerId = await ensureUser(USERS.devOwner);
  const collaboratorId = await ensureUser(USERS.devCollaborator);

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

  await seedChatSession({
    messages: [
      { content: "Plan a 4-day SF itinerary focused on food.", role: "user" },
      { content: "Here’s a structured 4-day plan you can refine…", role: "assistant" },
    ],
    sessionId: "44444444-4444-4444-4444-444444444444",
    tripId,
    userId: ownerId,
  });
}

async function runE2eSeed(): Promise<void> {
  const userId = await ensureUser(USERS.e2eUser);
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

async function main(): Promise<void> {
  // Basic connectivity check to surface obvious misconfiguration early.
  const health = await fetch(`${env.supabaseUrl}/auth/v1/health`, { method: "GET" });
  if (!health.ok) {
    throw new Error(
      `Supabase auth health failed (${health.status} ${health.statusText}). Is local Supabase running?`
    );
  }

  if (profile === "dev") {
    await runDevSeed();
    console.log(
      [
        "Seed complete (dev).",
        `- user: ${USERS.devOwner.email} / ${SEED_PASSWORD}`,
        `- user: ${USERS.devCollaborator.email} / ${SEED_PASSWORD}`,
      ].join("\n")
    );
    return;
  }

  await runE2eSeed();
  console.log(
    ["Seed complete (e2e).", `- user: ${USERS.e2eUser.email} / ${SEED_PASSWORD}`].join(
      "\n"
    )
  );
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`${message}\n`);
  process.exit(1);
});
