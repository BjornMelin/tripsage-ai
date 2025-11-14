/**
 * @fileoverview Text embedding generation API endpoint using OpenAI embeddings.
 */

import "server-only";

import { openai } from "@ai-sdk/openai";
import { embed } from "ai";
import { NextResponse } from "next/server";
import { withTelemetrySpan } from "@/lib/telemetry/span";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** Request payload for embedding generation. */
type EmbeddingRequest = {
  text?: string;
  property?: {
    id?: string;
    name?: string;
    description?: string;
    amenities?: string[] | string;
  };
};

/**
 * Generates text embeddings using OpenAI's text-embedding-3-small model.
 *
 * @param req - The incoming request containing text or property data.
 * @return Response with embedding vector and metadata, or error response.
 */
export function POST(req: Request) {
  return withTelemetrySpan(
    "embeddings.generate",
    { attributes: { route: "/api/embeddings" } },
    async () => {
      try {
        const body = (await req.json()) as EmbeddingRequest;
        const text =
          body.text ??
          (body.property
            ? `${body.property.name ?? ""}. Description: ${body.property.description ?? ""}. Amenities: ${Array.isArray(body.property.amenities) ? body.property.amenities.join(", ") : (body.property.amenities ?? "")}`
            : "");
        if (!text || !text.trim()) {
          return NextResponse.json(
            { error: "missing text or property" },
            { status: 400 }
          );
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

        return NextResponse.json({
          embedding,
          id: body.property?.id,
          modelId: "text-embedding-3-small",
          success: true,
          usage,
        });
      } catch (error) {
        return NextResponse.json(
          { error: error instanceof Error ? error.message : "internal error" },
          { status: 500 }
        );
      }
    }
  );
}
