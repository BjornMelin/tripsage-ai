/**
 * @fileoverview Embedding generation utility for RAG semantic search.
 *
 * Generates vector embeddings for accommodation property descriptions using
 * Supabase/gte-small model (384 dimensions). Supports both direct generation
 * (Node.js runtime) and Supabase Edge Function invocation.
 */

import "server-only";

import { getServerEnvVarWithFallback } from "@/lib/env/server";

/**
 * Generate embedding for text using Supabase/gte-small model.
 *
 * This function attempts to use a Supabase Edge Function for embedding
 * generation. If the Edge Function is not available, it falls back to
 * direct generation using @xenova/transformers (Node.js only).
 *
 * @param text - Text to generate embedding for
 * @returns Promise resolving to embedding vector (384 dimensions)
 * @throws {Error} If embedding generation fails
 */
export async function generateEmbedding(text: string): Promise<number[]> {
  if (!text || text.trim().length === 0) {
    throw new Error("Text cannot be empty");
  }

  const supabaseUrl = getServerEnvVarWithFallback("NEXT_PUBLIC_SUPABASE_URL", "");
  const supabaseAnonKey = getServerEnvVarWithFallback(
    "NEXT_PUBLIC_SUPABASE_ANON_KEY",
    ""
  );

  // Try Supabase Edge Function first (preferred for serverless)
  if (supabaseUrl && supabaseAnonKey) {
    try {
      const response = await fetch(`${supabaseUrl}/functions/v1/generate-embeddings`, {
        body: JSON.stringify({ text }),
        headers: {
          // biome-ignore lint/style/useNamingConvention: HTTP header name
          Authorization: `Bearer ${supabaseAnonKey}`,
          "Content-Type": "application/json",
        },
        method: "POST",
      });

      if (response.ok) {
        const data = (await response.json()) as { embedding: number[] };
        if (Array.isArray(data.embedding) && data.embedding.length === 384) {
          return data.embedding;
        }
      }
    } catch (error) {
      // Fall through to direct generation
      console.warn("Supabase Edge Function embedding generation failed:", error);
    }
  }

  // Fallback: Direct generation using @xenova/transformers (Node.js only)
  // This requires the transformers package to be installed
  try {
    // Dynamic import to avoid bundling in Edge runtime
    // Use any type for optional dependency that may not be installed
    const transformersModule = (await import("@xenova/transformers").catch(() => {
      throw new Error(
        "@xenova/transformers is not installed. Install it or use Supabase Edge Function."
      );
    })) as { pipeline: (...args: unknown[]) => Promise<unknown> };

    // Use singleton pattern for the pipeline (reuse model instance)
    const generateEmbeddingPipeline = (await transformersModule.pipeline(
      "feature-extraction",
      "Supabase/gte-small",
      { quantized: true } // Use quantized model for faster loading
    )) as (
      input: string,
      options?: Record<string, unknown>
    ) => Promise<{
      data: Float32Array | Float64Array | Int32Array;
    }>;

    const output = await generateEmbeddingPipeline(text, {
      normalize: true,
      pooling: "mean",
    });

    // Extract embedding vector from output
    const embedding = Array.from(output.data) as number[];

    if (embedding.length !== 384) {
      throw new Error(`Expected 384 dimensions, got ${embedding.length}`);
    }

    return embedding;
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    throw new Error(
      `Embedding generation failed: ${errorMessage}. ` +
        "Ensure @xenova/transformers is installed or Supabase Edge Function is configured."
    );
  }
}

/**
 * Generate embeddings for multiple texts in batch.
 *
 * @param texts - Array of texts to generate embeddings for
 * @returns Promise resolving to array of embedding vectors
 */
export function generateEmbeddings(texts: string[]): Promise<number[][]> {
  return Promise.all(texts.map((text) => generateEmbedding(text)));
}
