/** @vitest-environment jsdom */

import { describe, expect, it } from "vitest";
import { useRealtimeChannel } from "@/hooks/supabase/use-realtime-channel";

describe("useRealtimeChannel", () => {
  it("exports a callable hook without throwing on import", () => {
    expect(typeof useRealtimeChannel).toBe("function");
  });
});
