import { describe, expect, it } from "vitest";

describe("lookupPoiContext (stub)", () => {
  it("returns empty pois and provider stub", async () => {
    const { lookupPoiContext } = await import("@/lib/tools/poi-lookup");
    const out = await lookupPoiContext.execute?.(
      { destination: "Paris", radiusMeters: 1000 },
      { messages: [], toolCallId: "t-1" }
    );
    expect(out).toBeTruthy();
    const o = out as { provider?: string; pois?: unknown[]; inputs?: unknown };
    expect(o.provider).toBe("stub");
    expect(Array.isArray(o.pois)).toBe(true);
    expect((o.pois as unknown[]).length).toBe(0);
  });
});
