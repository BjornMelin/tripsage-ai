/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import type { ServerLogger } from "@/lib/telemetry/logger";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { createMockSupabaseClient } from "@/test/mocks/supabase";
import {
  createMessage,
  createSession,
  deleteSession,
  getSession,
  listMessages,
  listSessions,
} from "../_handlers";

type UntypedSupabaseInsert = {
  from: (table: string) => {
    insert: (values: unknown) => Promise<unknown>;
  };
};

describe("sessions _handlers", () => {
  const logger = {
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
  } satisfies ServerLogger;

  it("create/list session happy path", async () => {
    const s: TypedServerSupabase = createMockSupabaseClient({ user: { id: "u1" } });
    const res1 = await createSession({ logger, supabase: s, userId: "u1" }, "Trip");
    expect(res1.status).toBe(201);
    const res2 = await listSessions({ logger, supabase: s, userId: "u1" });
    expect(res2.status).toBe(200);
  });

  it("get/delete session auth gating", async () => {
    const s: TypedServerSupabase = createMockSupabaseClient({ user: { id: "u2" } });
    const created = await createSession({ logger, supabase: s, userId: "u2" }, "Trip");
    const { id } = (await created.json()) as { id: string };
    const g = await getSession({ logger, supabase: s, userId: "u2" }, id);
    expect(g.status).toBe(200);
    const d = await deleteSession({ logger, supabase: s, userId: "u2" }, id);
    expect(d.status).toBe(204);
  });

  it("list/create messages happy path", async () => {
    const s: TypedServerSupabase = createMockSupabaseClient({ user: { id: "u3" } });
    const created = await createSession({ logger, supabase: s, userId: "u3" }, "Trip");
    const { id } = (await created.json()) as { id: string };
    const r1 = await createMessage({ logger, supabase: s, userId: "u3" }, id, {
      parts: [{ text: "hi", type: "text" }],
      role: "user",
    });
    expect(r1.status).toBe(201);
    const r2 = await listMessages({ logger, supabase: s, userId: "u3" }, id);
    expect(r2.status).toBe(200);
  });

  it("includes tool output parts for assistant messages", async () => {
    const s: TypedServerSupabase = createMockSupabaseClient({ user: { id: "u4" } });
    const created = await createSession({ logger, supabase: s, userId: "u4" }, "Trip");
    const { id: sessionId } = (await created.json()) as { id: string };

    await unsafeCast<UntypedSupabaseInsert>(s)
      .from("chat_messages")
      .insert([
        {
          content: JSON.stringify([{ text: "hi", type: "text" }]),
          id: 1,
          metadata: {},
          role: "user",
          session_id: sessionId,
          user_id: "u4",
        },
        {
          content: JSON.stringify([{ text: "tool step", type: "text" }]),
          id: 2,
          metadata: {},
          role: "assistant",
          session_id: sessionId,
          user_id: "u4",
        },
      ]);

    await s.from("chat_tool_calls").insert({
      arguments: { query: "london" },
      message_id: 2,
      result: { ok: true },
      status: "completed",
      tool_id: "call-1",
      tool_name: "webSearch",
    });

    const res = await listMessages({ logger, supabase: s, userId: "u4" }, sessionId);
    expect(res.status).toBe(200);
    const body = (await res.json()) as Array<{
      role: string;
      parts: Array<{ type: string; state?: string }>;
    }>;

    const assistant = body.find((m) => m.role === "assistant");
    expect(assistant).toBeTruthy();
    const toolPart = assistant?.parts.find(
      (p) => p.type === "dynamic-tool" || p.type.startsWith("tool-")
    );
    expect(toolPart).toBeTruthy();
    expect(toolPart).toMatchObject({
      input: { query: "london" },
      output: { ok: true },
      toolCallId: "call-1",
      toolName: "webSearch",
      type: "dynamic-tool",
    });
    expect(
      assistant?.parts.some(
        (p) => p.type === "dynamic-tool" || p.type.startsWith("tool-")
      )
    ).toBe(true);
  });

  it("tolerates legacy model tool-call parts in stored content", async () => {
    const s: TypedServerSupabase = createMockSupabaseClient({ user: { id: "u6" } });
    const created = await createSession({ logger, supabase: s, userId: "u6" }, "Trip");
    const { id: sessionId } = (await created.json()) as { id: string };

    await unsafeCast<UntypedSupabaseInsert>(s)
      .from("chat_messages")
      .insert([
        {
          content: JSON.stringify([{ text: "hi", type: "text" }]),
          id: 1,
          metadata: {},
          role: "user",
          session_id: sessionId,
          user_id: "u6",
        },
        {
          // Stored by older implementations as model message parts (invalid for UIMessage parts).
          content: JSON.stringify([
            {
              args: { query: "london" },
              toolCallId: "call-legacy-1",
              toolName: "webSearch",
              type: "tool-call",
            },
          ]),
          id: 2,
          metadata: {},
          role: "assistant",
          session_id: sessionId,
          user_id: "u6",
        },
      ]);

    await s.from("chat_tool_calls").insert({
      arguments: { query: "london" },
      message_id: 2,
      result: { ok: true },
      status: "completed",
      tool_id: "call-legacy-1",
      tool_name: "webSearch",
    });

    const res = await listMessages({ logger, supabase: s, userId: "u6" }, sessionId);
    expect(res.status).toBe(200);
    const body = (await res.json()) as Array<{
      role: string;
      parts: Array<{ type: string; state?: string; toolCallId?: string }>;
    }>;

    const assistant = body.find((m) => m.role === "assistant");
    expect(assistant).toBeTruthy();
    expect(
      assistant?.parts.some(
        (p) => p.type === "dynamic-tool" && p.toolCallId === "call-legacy-1"
      )
    ).toBe(true);
  });

  it("filters superseded assistant messages", async () => {
    const s: TypedServerSupabase = createMockSupabaseClient({ user: { id: "u5" } });
    const created = await createSession({ logger, supabase: s, userId: "u5" }, "Trip");
    const { id: sessionId } = (await created.json()) as { id: string };

    await unsafeCast<UntypedSupabaseInsert>(s)
      .from("chat_messages")
      .insert([
        {
          content: JSON.stringify([{ text: "hi", type: "text" }]),
          id: 1,
          metadata: {},
          role: "user",
          session_id: sessionId,
          user_id: "u5",
        },
        {
          content: JSON.stringify([{ text: "first answer", type: "text" }]),
          id: 2,
          metadata: { status: "superseded", supersededBy: "db:next" },
          role: "assistant",
          session_id: sessionId,
          user_id: "u5",
        },
        {
          content: JSON.stringify([{ text: "second answer", type: "text" }]),
          id: 3,
          metadata: {},
          role: "assistant",
          session_id: sessionId,
          user_id: "u5",
        },
      ]);

    const res = await listMessages({ logger, supabase: s, userId: "u5" }, sessionId);
    expect(res.status).toBe(200);
    const body = (await res.json()) as Array<{ role: string }>;

    const assistants = body.filter((m) => m.role === "assistant");
    expect(assistants.length).toBe(1);
  });
});
