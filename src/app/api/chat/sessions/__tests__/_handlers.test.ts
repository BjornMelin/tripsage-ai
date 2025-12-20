/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createMockSupabaseClient } from "@/test/mocks/supabase";
import {
  createMessage,
  createSession,
  deleteSession,
  getSession,
  listMessages,
  listSessions,
} from "../_handlers";

describe("sessions _handlers", () => {
  it("create/list session happy path", async () => {
    const s: TypedServerSupabase = createMockSupabaseClient({ user: { id: "u1" } });
    const res1 = await createSession({ supabase: s, userId: "u1" }, "Trip");
    expect(res1.status).toBe(201);
    const res2 = await listSessions({ supabase: s, userId: "u1" });
    expect(res2.status).toBe(200);
  });

  it("get/delete session auth gating", async () => {
    const s: TypedServerSupabase = createMockSupabaseClient({ user: { id: "u2" } });
    const created = await createSession({ supabase: s, userId: "u2" }, "Trip");
    const { id } = (await created.json()) as { id: string };
    const g = await getSession({ supabase: s, userId: "u2" }, id);
    expect(g.status).toBe(200);
    const d = await deleteSession({ supabase: s, userId: "u2" }, id);
    expect(d.status).toBe(204);
  });

  it("list/create messages happy path", async () => {
    const s: TypedServerSupabase = createMockSupabaseClient({ user: { id: "u3" } });
    const created = await createSession({ supabase: s, userId: "u3" }, "Trip");
    const { id } = (await created.json()) as { id: string };
    const r1 = await createMessage({ supabase: s, userId: "u3" }, id, {
      parts: [{ text: "hi", type: "text" }],
      role: "user",
    });
    expect(r1.status).toBe(201);
    const r2 = await listMessages({ supabase: s, userId: "u3" }, id);
    expect(r2.status).toBe(200);
  });
});
