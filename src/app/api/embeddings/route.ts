/**
 * @fileoverview API route that generates and optionally persists text embeddings.
 */

import "server-only";

import {
  embeddingsRequestSchema,
  type PersistableEmbeddingsProperty,
  persistableEmbeddingsPropertySchema,
} from "@schemas/embeddings";
import { embed } from "ai";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import {
  getTextEmbeddingModel,
  getTextEmbeddingModelId,
  TEXT_EMBEDDING_DIMENSIONS,
} from "@/lib/ai/embeddings/text-embedding-model";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  forbiddenResponse,
  unauthorizedResponse,
} from "@/lib/api/route-helpers";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { toPgvector } from "@/lib/rag/pgvector";
import { isValidInternalKey } from "@/lib/security/internal-key";
import { createAdminSupabase } from "@/lib/supabase/admin";
import type { TablesInsert } from "@/lib/supabase/database.types";
import { upsertSingle } from "@/lib/supabase/typed-helpers";
import { createServerLogger } from "@/lib/telemetry/logger";

const MAX_INPUT_LENGTH = 8000;
const EMBED_TIMEOUT_MS = 2_000;

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
 * @param embedding - Embedding vector (must match `TEXT_EMBEDDING_DIMENSIONS`).
 * @throws Error if database operation fails.
 */
async function persistAccommodationEmbedding(
  property: PersistableEmbeddingsProperty,
  embedding: number[]
): Promise<void> {
  const supabase = createAdminSupabase();
  const payload: TablesInsert<"accommodation_embeddings"> = {
    amenities: normalizeAmenities(property.amenities),
    description: property.description ?? null,
    embedding: toPgvector(embedding),
    id: property.id,
    name: property.name ?? null,
    source: normalizeSource(property.source),
    updated_at: new Date().toISOString(),
  };

  const { error } = await upsertSingle(
    supabase,
    "accommodation_embeddings",
    payload,
    "id",
    { validate: false }
  );

  if (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(message);
  }
}

/**
 * Generates text embeddings using the configured embedding provider (AI Gateway/OpenAI),
 * falling back to deterministic offline embeddings when no provider keys are set.
 *
 * @param req - Request containing text or property data.
 * @returns Response with embedding vector and metadata, or error.
 */
export const POST = withApiGuards({
  auth: false,
  degradedMode: "fail_closed",
  rateLimit: "embeddings",
  schema: embeddingsRequestSchema,
  telemetry: "embeddings.generate",
})(async (req: NextRequest, _context, body) => {
  const logger = createServerLogger("embeddings.generate");
  const internalKey = getServerEnvVarWithFallback("EMBEDDINGS_API_KEY", "");
  if (!internalKey) {
    return errorResponse({
      error: "embeddings_disabled",
      reason: "Embeddings endpoint disabled",
      status: 503,
    });
  }

  const provided = req.headers.get("x-internal-key");
  if (!isValidInternalKey(provided, internalKey)) {
    return provided
      ? forbiddenResponse("Invalid internal key")
      : unauthorizedResponse();
  }

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

  // Generate embedding via AI SDK v6 using Gateway/OpenAI when configured,
  // otherwise deterministic local embeddings (1536-d).
  const { embedding, usage } = await embed({
    abortSignal: AbortSignal.timeout(EMBED_TIMEOUT_MS),
    model: getTextEmbeddingModel(),
    value: text,
  });
  if (!Array.isArray(embedding) || embedding.length !== TEXT_EMBEDDING_DIMENSIONS) {
    return errorResponse({
      err: new Error(
        `Embedding dimension mismatch: expected ${TEXT_EMBEDDING_DIMENSIONS}, got ${Array.isArray(embedding) ? embedding.length : -1}`
      ),
      error: "internal",
      reason: "Embedding dimension mismatch",
      status: 500,
    });
  }

  let persisted = false;
  const persistablePropertyResult = body.property
    ? persistableEmbeddingsPropertySchema.safeParse(body.property)
    : null;
  if (persistablePropertyResult?.success) {
    try {
      await persistAccommodationEmbedding(persistablePropertyResult.data, embedding);
      persisted = true;
    } catch (persistError) {
      logger.error("persist_failed", {
        error: persistError instanceof Error ? persistError.message : "unknown_error",
        propertyId: persistablePropertyResult.data.id,
      });
    }
  }

  return NextResponse.json({
    embedding,
    id: body.property?.id,
    modelId: getTextEmbeddingModelId(),
    persisted,
    success: true,
    usage,
  });
});
