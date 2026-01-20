/**
 * @fileoverview Deterministic, offline-safe text embeddings (1536-d) for local dev/tests.
 *
 * This is a non-semantic fallback designed to keep the app runnable when no paid
 * embedding provider is configured. It MUST NOT be used to evaluate retrieval quality.
 */

import { createHash } from "node:crypto";

export const DETERMINISTIC_TEXT_EMBEDDING_DIMENSIONS = 1536;
export const DETERMINISTIC_TEXT_EMBEDDING_MODEL_ID =
  "tripsage/deterministic-embedding-1536-v1" as const;

function sha256(data: Uint8Array): Uint8Array {
  return createHash("sha256").update(data).digest();
}

function utf8(value: string): Uint8Array {
  return new TextEncoder().encode(value);
}

function concatBytes(a: Uint8Array, b: Uint8Array): Uint8Array {
  const out = new Uint8Array(a.length + b.length);
  out.set(a, 0);
  out.set(b, a.length);
  return out;
}

function readU32be(bytes: Uint8Array, offset: number): number {
  return (
    (((bytes[offset] ?? 0) << 24) |
      ((bytes[offset + 1] ?? 0) << 16) |
      ((bytes[offset + 2] ?? 0) << 8) |
      (bytes[offset + 3] ?? 0)) >>>
    0
  );
}

function normalizeVector(vec: number[]): number[] {
  let sumSquares = 0;
  for (const v of vec) sumSquares += v * v;
  const norm = Math.sqrt(sumSquares);
  if (!Number.isFinite(norm) || norm <= 0) return vec;
  return vec.map((v) => v / norm);
}

export function deterministicTextEmbedding(text: string): number[] {
  // Stable across platforms/Node versions: use UTF-8 + SHA-256 only.
  const seedPrefix = utf8("tripsage:deterministic-embeddings:v1\0");
  const seed = sha256(concatBytes(seedPrefix, utf8(text)));

  const result: number[] = new Array<number>(DETERMINISTIC_TEXT_EMBEDDING_DIMENSIONS);
  let i = 0;
  let counter = 0;

  while (i < result.length) {
    const counterBytes = utf8(`\0${counter}`);
    const digest = sha256(concatBytes(seed, counterBytes));

    // digest is 32 bytes -> 8 u32 values -> 8 floats
    for (let j = 0; j + 3 < digest.length && i < result.length; j += 4) {
      const u32 = readU32be(digest, j);
      const unit = u32 / 0xffff_ffff; // [0,1]
      result[i] = unit * 2 - 1; // [-1,1]
      i += 1;
    }

    counter += 1;
  }

  return normalizeVector(result);
}
