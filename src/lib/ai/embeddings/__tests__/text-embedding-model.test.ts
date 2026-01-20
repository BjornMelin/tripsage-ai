/** @vitest-environment node */

import { embed } from "ai";
import { afterEach, describe, expect, it, vi } from "vitest";
import { __resetServerEnvCacheForTest } from "@/lib/env/server";
import {
  getTextEmbeddingModel,
  getTextEmbeddingModelId,
  TEXT_EMBEDDING_DIMENSIONS,
  TEXT_EMBEDDING_MODEL_ID,
} from "../text-embedding-model";

vi.mock("server-only", () => ({}));

afterEach(() => {
  vi.unstubAllEnvs();
  __resetServerEnvCacheForTest();
});

describe("getTextEmbeddingModel", () => {
  it("returns deterministic EmbeddingModelV3 when no provider keys are configured", async () => {
    vi.stubEnv("AI_GATEWAY_API_KEY", "");
    vi.stubEnv("OPENAI_API_KEY", "");
    __resetServerEnvCacheForTest();

    const model = getTextEmbeddingModel();
    expect(typeof model).not.toBe("string");
    expect(getTextEmbeddingModelId()).toBe("tripsage/deterministic-embedding-1536-v1");

    const { embedding: e1 } = await embed({ model, value: "hello world" });
    const { embedding: e2 } = await embed({ model, value: "hello world" });
    const { embedding: e3 } = await embed({ model, value: "different input" });

    expect(e1).toHaveLength(TEXT_EMBEDDING_DIMENSIONS);
    expect(e2).toHaveLength(TEXT_EMBEDDING_DIMENSIONS);
    expect(e3).toHaveLength(TEXT_EMBEDDING_DIMENSIONS);
    expect(e1).toEqual(e2);
    expect(e1).not.toEqual(e3);

    // Vector is normalized to unit length (within tolerance).
    const norm = Math.sqrt(e1.reduce((acc, v) => acc + v * v, 0));
    expect(norm).toBeGreaterThan(0.99);
    expect(norm).toBeLessThan(1.01);

    // Values are bounded in [-1, 1].
    for (const v of e1) {
      expect(v).toBeGreaterThanOrEqual(-1);
      expect(v).toBeLessThanOrEqual(1);
    }
  });

  it("prefers AI Gateway when configured", () => {
    vi.stubEnv("AI_GATEWAY_API_KEY", "aaaaaaaaaaaaaaaaaaaa");
    vi.stubEnv("OPENAI_API_KEY", "");
    __resetServerEnvCacheForTest();

    expect(getTextEmbeddingModel()).toBe(TEXT_EMBEDDING_MODEL_ID);
    expect(getTextEmbeddingModelId()).toBe(TEXT_EMBEDDING_MODEL_ID);
  });

  it("falls back to direct OpenAI when configured and Gateway is not", () => {
    vi.stubEnv("AI_GATEWAY_API_KEY", "");
    vi.stubEnv("OPENAI_API_KEY", "sk-test-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
    __resetServerEnvCacheForTest();

    const model = getTextEmbeddingModel();
    expect(typeof model).not.toBe("string");
    expect(getTextEmbeddingModelId()).toBe("text-embedding-3-small");
  });
});
