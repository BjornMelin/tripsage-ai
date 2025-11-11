import { describe, expect, it } from "vitest";
import { wrapToolsWithUserId } from "../injection";

describe("wrapToolsWithUserId", () => {
  it("injects userId into selected tools and preserves execute behavior", async () => {
    const calls: unknown[] = [];
    const dummy = {
      execute: (a: unknown) => {
        calls.push(a);
        return Promise.resolve({ ok: true } as const);
      },
    } as const;
    const tools = { createTravelPlan: dummy, otherTool: { x: 1 } } as Record<
      string,
      unknown
    >;
    const wrapped = wrapToolsWithUserId(tools, "u-inject", ["createTravelPlan"]);
    const res = await (
      wrapped.createTravelPlan as { execute: (a: unknown) => Promise<unknown> }
    ).execute({ title: "t" });
    expect(res).toEqual({ ok: true });
    expect(calls.length).toBe(1);
    expect(calls[0]).toMatchObject({ title: "t", userId: "u-inject" });
    // otherTool untouched
    expect(wrapped.otherTool).toEqual({ x: 1 });
  });
});
