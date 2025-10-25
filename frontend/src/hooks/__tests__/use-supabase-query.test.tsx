/**
 * @fileoverview Tests for the useSupabaseQuery hook.
 */

import { describe, expect, it, vi } from "vitest";
import { render } from "@/test/test-utils";
import React from "react";

/**
 * Test component to render trip count using useSupabaseQuery.
 * @return JSX element displaying the count of trips.
 */
function UsersList() {
  const { useSupabaseQuery } = require("@/hooks/use-supabase-query");
  const { data, isSuccess } = useSupabaseQuery({
    table: "trips" as any,
    columns: "id",
  });
  return <div aria-label="count">{isSuccess ? (data?.length || 0) : "-"}</div>;
}

describe("useSupabaseQuery", () => {
  it("fetches when user exists and returns data", async () => {
    // Mock supabase client for this test to return a user and data list
    vi.doMock("@/lib/supabase/client", () => ({
      useSupabase: () => ({
        auth: {
          getUser: vi.fn(async () => ({ data: { user: { id: "u1" } } })),
          onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
        },
        from: vi.fn(() => ({
          select: vi.fn(async () => ({ data: [{ id: 1 }, { id: 2 }], error: null })),
        })),
      }),
    }));

    const { findByLabelText } = render(<UsersList />);
    expect(await findByLabelText("count")).toHaveTextContent("2");
  });
});
