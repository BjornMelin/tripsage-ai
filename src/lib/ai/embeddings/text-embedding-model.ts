/**
 * @fileoverview Embedding model selection for server-only usage (Gateway/OpenAI + deterministic fallback).
 */

import "server-only";

import { openai } from "@ai-sdk/openai";
import type { EmbeddingModelV3, EmbeddingModelV3Result } from "@ai-sdk/provider";
import type { EmbeddingModel } from "ai";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import {
  DETERMINISTIC_TEXT_EMBEDDING_DIMENSIONS,
  DETERMINISTIC_TEXT_EMBEDDING_MODEL_ID,
  deterministicTextEmbedding,
} from "./deterministic";

export const TEXT_EMBEDDING_DIMENSIONS = 1536;
export const TEXT_EMBEDDING_MODEL_ID = "openai/text-embedding-3-small" as const;

function createDeterministicEmbeddingModel(): EmbeddingModelV3 {
  return {
    doEmbed: (options): PromiseLike<EmbeddingModelV3Result> => {
      const embeddings = options.values.map((value) =>
        deterministicTextEmbedding(value)
      );

      // Token usage is provider-specific; for deterministic embeddings we return a conservative
      // approximation based on 4 chars/token.
      let tokens = 0;
      for (const v of options.values) tokens += Math.ceil(v.length / 4);

      return Promise.resolve({
        embeddings,
        usage: { tokens },
        warnings: [],
      });
    },
    maxEmbeddingsPerCall: Infinity,
    modelId: DETERMINISTIC_TEXT_EMBEDDING_MODEL_ID,
    provider: "tripsage",
    specificationVersion: "v3",
    supportsParallelCalls: true,
  };
}

let cachedAiGatewayKey: boolean | undefined;
let cachedOpenAiKey: boolean | undefined;

// biome-ignore lint/style/useNamingConvention: test-only reset helper
export function __resetEmbeddingKeyCacheForTest() {
  cachedAiGatewayKey = undefined;
  cachedOpenAiKey = undefined;
}

function hasAiGatewayKey(): boolean {
  if (cachedAiGatewayKey === undefined) {
    cachedAiGatewayKey = Boolean(
      getServerEnvVarWithFallback("AI_GATEWAY_API_KEY", undefined)
    );
  }
  return cachedAiGatewayKey;
}

function hasOpenAiKey(): boolean {
  if (cachedOpenAiKey === undefined) {
    cachedOpenAiKey = Boolean(getServerEnvVarWithFallback("OPENAI_API_KEY", undefined));
  }
  return cachedOpenAiKey;
}

export function getTextEmbeddingModel(): EmbeddingModel {
  // Prefer AI Gateway when configured: string model IDs resolve via the global provider.
  if (hasAiGatewayKey()) return TEXT_EMBEDDING_MODEL_ID;

  // Direct OpenAI fallback when configured.
  if (hasOpenAiKey()) {
    return openai.embeddingModel("text-embedding-3-small");
  }

  // Final fallback: deterministic embeddings for local dev + tests.
  return createDeterministicEmbeddingModel();
}

export function getTextEmbeddingModelId(): string {
  const model = getTextEmbeddingModel();
  if (typeof model === "string") return model;
  return model.modelId;
}

export const DETERMINISTIC_EMBEDDING_DIMENSIONS =
  DETERMINISTIC_TEXT_EMBEDDING_DIMENSIONS;
export const DETERMINISTIC_EMBEDDING_MODEL_ID = DETERMINISTIC_TEXT_EMBEDDING_MODEL_ID;
