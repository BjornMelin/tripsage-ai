import { describe, expect, it, vi } from "vitest";
import * as route from "@/app/api/embeddings/route";

vi.mock("ai", () => ({
  embed: vi.fn(async () => ({
    embedding: Array.from({ length: 1536 }, () => Math.random()),
    usage: { tokens: { input: 12 } },
  })),
}));

describe("POST /api/embeddings", () => {
  it("returns 400 on missing input", async () => {
    const res = await route.POST(
      new Request("http://localhost/api/embeddings", {
        body: JSON.stringify({ text: "" }),
        method: "POST",
      })
    );
    expect(res.status).toBe(400);
  });

  it("returns 1536-d embedding", async () => {
    const res = await route.POST(
      new Request("http://localhost/api/embeddings", {
        body: JSON.stringify({ text: "hello world" }),
        method: "POST",
      })
    );
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(Array.isArray(json.embedding)).toBe(true);
    expect(json.embedding).toHaveLength(1536);
    expect(json.success).toBe(true);
  });
});
