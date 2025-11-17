/**
 * @fileoverview Text embedding generation API endpoint using OpenAI embeddings.
 */

import "server-only";

import { openai } from "@ai-sdk/openai";
import { embed } from "ai";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { createAdminSupabase } from "@/lib/supabase/admin";
import type { InsertTables } from "@/lib/supabase/database.types";

const MAX_INPUT_LENGTH = 8000;

/** Request payload for embedding generation. */
type EmbeddingRequest = {
  text?: string;
  property?: {
    id?: string;
    name?: string;
    description?: string;
    amenities?: string[] | string;
    source?: string;
  };
};

type PersistableProperty = Required<
  Pick<NonNullable<EmbeddingRequest["property"]>, "id">
> &
  NonNullable<EmbeddingRequest["property"]>;

function normalizeSource(source?: string): "hotel" | "vrbo" {
  if (source && source.toLowerCase() === "vrbo") {
    return "vrbo";
  }
  return "hotel";
}

function normalizeAmenities(amenities?: string[] | string): string | null {
  if (!amenities) {
    return null;
  }
  if (Array.isArray(amenities)) {
    const cleaned = amenities
      .map((item) => item?.trim())
      .filter((item): item is string => Boolean(item));
    return cleaned.length > 0 ? cleaned.join(", ") : null;
  }
  const trimmed = amenities.trim();
  return trimmed.length > 0 ? trimmed : null;
}

async function persistAccommodationEmbedding(
  property: PersistableProperty,
  embedding: number[]
): Promise<void> {
  const supabase = createAdminSupabase();
  const payload: InsertTables<"accommodation_embeddings"> = {
    amenities: normalizeAmenities(property.amenities),
    description: property.description ?? null,
    embedding,
    id: property.id,
    name: property.name ?? null,
    source: normalizeSource(property.source),
    updated_at: new Date().toISOString(),
  };

  const { error } = await supabase
    .from("accommodation_embeddings")
    .upsert(payload, { onConflict: "id" });

  if (error) {
    throw new Error(error.message);
  }
}

/**
 * Generates text embeddings using OpenAI's text-embedding-3-small model.
 *
 * @param req - The incoming request containing text or property data.
 * @param routeContext - Route context from withApiGuards
 * @returns Response with embedding vector and metadata, or error response.
 */
export const POST = withApiGuards({
  auth: false,
  rateLimit: "embeddings",
  telemetry: "embeddings.generate",
})(async (req: NextRequest) => {
  const internalKey = process.env.EMBEDDINGS_API_KEY;
  if (internalKey) {
    const provided = req.headers.get("x-internal-key");
    if (provided !== internalKey) {
      return NextResponse.json({ error: "unauthorized" }, { status: 401 });
    }
  }

  const body = (await req.json()) as EmbeddingRequest;
  const text =
    body.text ??
    (body.property
      ? `${body.property.name ?? ""}. Description: ${body.property.description ?? ""}. Amenities: ${Array.isArray(body.property.amenities) ? body.property.amenities.join(", ") : (body.property.amenities ?? "")}`
      : "");
  if (!text || !text.trim()) {
    return NextResponse.json({ error: "missing text or property" }, { status: 400 });
  }

  if (text.length > MAX_INPUT_LENGTH) {
    return NextResponse.json({ error: "text too long" }, { status: 400 });
  }

  // Generate embedding via AI SDK v6 using OpenAI text-embedding-3-small (1536-d)
  const { embedding, usage } = await embed({
    model: openai.textEmbeddingModel("text-embedding-3-small"),
    value: text,
  });
  if (!Array.isArray(embedding) || embedding.length !== 1536) {
    return NextResponse.json(
      {
        error: "embedding dimension mismatch",
        length: Array.isArray(embedding) ? embedding.length : -1,
      },
      { status: 500 }
    );
  }

  let persisted = false;
  if (body.property?.id) {
    try {
      await persistAccommodationEmbedding(
        body.property as PersistableProperty,
        embedding
      );
      persisted = true;
    } catch (persistError) {
      console.error(
        `[Embeddings] Failed to persist property ${body.property.id}:`,
        persistError
      );
    }
  }

  return NextResponse.json({
    embedding,
    id: body.property?.id,
    modelId: "text-embedding-3-small",
    persisted,
    success: true,
    usage,
  });
});
