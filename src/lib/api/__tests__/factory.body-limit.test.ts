/** @vitest-environment node */

import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";

describe("withApiGuards body limits", () => {
  it("honors maxBodyBytes override for schema parsing", async () => {
    const handler = withApiGuards({
      maxBodyBytes: 10,
      schema: z.strictObject({ ok: z.boolean() }),
    })(async () => new Response("ok", { status: 200 }));

    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(JSON.stringify({ ok: true })));
        controller.close();
      },
    });

    const req = new NextRequest("https://example.com/api/test", {
      body: stream,
      duplex: "half",
      headers: { "content-type": "application/json" },
      method: "POST",
    });

    const res = await handler(req, { params: Promise.resolve({}) });
    expect(res.status).toBe(413);
  });
});
