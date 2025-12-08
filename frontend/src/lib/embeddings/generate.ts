/**
 * @fileoverview Embedding generation utility for RAG semantic search.
 *
 * Generates vector embeddings for accommodation property descriptions using
 * the `/api/embeddings` Next.js route backed by OpenAI text-embedding-3-small
 * (1536 dimensions).
 */

import "server-only";

import { getServerOrigin } from "@/lib/url/server-origin";

/**
 * Generate embedding for text using the `/api/embeddings` Route Handler.
 *
 * This ensures all server contexts share the same provider (OpenAI
 * text-embedding-3-small), telemetry, and future persistence hooks.
 *
 * @param text - Text to generate embedding for
 * @returns Promise resolving to a 1536-dimension embedding vector
 * @throws {Error} If embedding generation fails
 */
type EmbeddingsApiResponse = {
  embedding?: number[];
  error?: string;
};

import { getServerEnvVarWithFallback } from "@/lib/env/server";

export function getEmbeddingsApiUrl(): string {
  return new URL("/api/embeddings", getServerOrigin()).toString();
}

function resolveInternalEmbeddingsKey(): string | null {
  const configured = getServerEnvVarWithFallback("EMBEDDINGS_API_KEY", undefined);
  if (!configured) {
    return null;
  }
  const trimmed = configured.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function getEmbeddingsRequestHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const internalKey = resolveInternalEmbeddingsKey();
  if (internalKey) {
    headers["x-internal-key"] = internalKey;
  }
  return headers;
}

export async function generateEmbedding(text: string): Promise<number[]> {
  if (!text || text.trim().length === 0) {
    throw new Error("Text cannot be empty");
  }

  const endpoint = getEmbeddingsApiUrl();
  const headers = getEmbeddingsRequestHeaders();
  let response: Response;
  try {
    response = await fetch(endpoint, {
      body: JSON.stringify({ text }),
      headers,
      method: "POST",
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Failed to reach embeddings API: ${message}`);
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as EmbeddingsApiResponse;
    const error =
      payload.error ?? `Embedding API responded with status ${response.status}`;
    throw new Error(error);
  }

  const data = (await response.json()) as EmbeddingsApiResponse;
  if (!Array.isArray(data.embedding)) {
    throw new Error("Embedding API did not return a valid embedding vector");
  }
  if (data.embedding.length !== 1536) {
    throw new Error(`Expected 1536 dimensions, received ${data.embedding.length}`);
  }

  return data.embedding;
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
