/**
 * @fileoverview Text embedding generation endpoint.
 *
 * Generates embeddings using OpenAI text-embedding-3-small model.
 */

import "server-only";

import { openai } from "@ai-sdk/openai";
import { embed } from "ai";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, parseJsonBody } from "@/lib/api/route-helpers";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { createAdminSupabase } from "@/lib/supabase/admin";
import type { InsertTables } from "@/lib/supabase/database.types";
import { createServerLogger } from "@/lib/telemetry/logger";

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

/** Property with required ID for persistence. */
type PersistableProperty = Required<
  Pick<NonNullable<EmbeddingRequest["property"]>, "id">
> &
  NonNullable<EmbeddingRequest["property"]>;

/**
 * Normalizes source string to "hotel" or "vrbo".
 *
 * @param source - Source string to normalize.
 * @returns Normalized source type.
 */
function normalizeSource(source?: string): "hotel" | "vrbo" {
  if (source && source.toLowerCase() === "vrbo") {
    return "vrbo";
  }
  return "hotel";
}

/**
 * Normalizes amenities array or string to comma-separated string.
 *
 * @param amenities - Amenities array or string.
 * @returns Normalized amenities string or null.
 */
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

/**
 * Persists accommodation embedding to Supabase.
 *
 * @param property - Property data with required ID.
 * @param embedding - Embedding vector (1536 dimensions).
 * @throws Error if database operation fails.
 */
async function persistAccommodationEmbedding(
  property: PersistableProperty,
  embedding: number[]
): Promise<void> {
  const supabase = createAdminSupabase();
  const payload: InsertTables<"accommodation_embeddings"> = {
    amenities: normalizeAmenities(property.amenities),
    description: property.description ?? null,
    // Supabase CLI types surface pgvector as string; cast to satisfy client types while sending number[].
    embedding: embedding as unknown as string,
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
 * Generates text embeddings using OpenAI text-embedding-3-small model.
 *
 * @param req - Request containing text or property data.
 * @returns Response with embedding vector and metadata, or error.
 */
export const POST = withApiGuards({
  auth: false,
  rateLimit: "embeddings",
  telemetry: "embeddings.generate",
})(async (req: NextRequest) => {
  const logger = createServerLogger("embeddings.generate");
  const internalKey = getServerEnvVarWithFallback("EMBEDDINGS_API_KEY", undefined);
  if (internalKey) {
    const provided = req.headers.get("x-internal-key");
    if (provided !== internalKey) {
      return errorResponse({
        error: "unauthorized",
        reason: "Authentication required",
        status: 401,
      });
    }
  }

  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }
  const body = parsed.body as EmbeddingRequest;
  const text =
    body.text ??
    (body.property
      ? `${body.property.name ?? ""}. Description: ${body.property.description ?? ""}. Amenities: ${Array.isArray(body.property.amenities) ? body.property.amenities.join(", ") : (body.property.amenities ?? "")}`
      : "");
  if (!text || !text.trim()) {
    return errorResponse({
      error: "invalid_request",
      reason: "Missing text or property",
      status: 400,
    });
  }

  if (text.length > MAX_INPUT_LENGTH) {
    return errorResponse({
      error: "invalid_request",
      reason: `Text too long (max ${MAX_INPUT_LENGTH} characters)`,
      status: 400,
    });
  }

  // Generate embedding via AI SDK v6 using OpenAI text-embedding-3-small (1536-d)
  const { embedding, usage } = await embed({
    model: openai.textEmbeddingModel("text-embedding-3-small"),
    value: text,
  });
  if (!Array.isArray(embedding) || embedding.length !== 1536) {
    return errorResponse({
      err: new Error(
        `Embedding dimension mismatch: expected 1536, got ${Array.isArray(embedding) ? embedding.length : -1}`
      ),
      error: "internal",
      reason: "Embedding dimension mismatch",
      status: 500,
    });
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
      logger.error("persist_failed", {
        error: persistError instanceof Error ? persistError.message : "unknown_error",
        propertyId: body.property.id,
      });
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
