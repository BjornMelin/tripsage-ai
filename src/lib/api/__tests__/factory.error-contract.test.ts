/** @vitest-environment node */

import { NextRequest } from "next/server";
import { describe, expect, it, vi } from "vitest";
import { withApiGuards } from "@/lib/api/factory";

vi.mock("server-only", () => ({}));

describe("withApiGuards error contract", () => {
  it("converts unknown handler errors to canonical 500 responses", async () => {
    const handler = withApiGuards({})(() => {
      throw new Error("unexpected database state");
    });

    const req = new NextRequest("https://example.com/api/test", {
      method: "GET",
    });

    const res = await handler(req, { params: Promise.resolve({}) });
    const body = (await res.json()) as { error: string; reason: string };

    expect(res.status).toBe(500);
    expect(body).toEqual({
      error: "internal",
      reason: "Internal server error",
    });
  });
});
