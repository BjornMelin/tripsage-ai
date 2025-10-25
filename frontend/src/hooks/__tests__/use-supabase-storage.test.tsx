/**
 * @fileoverview Tests for the useSupabaseStorage hook.
 */

import { describe, expect, it, vi } from "vitest";
import { render } from "@/test/test-utils";
import React from "react";

/**
 * Test component to render file attachment count using useSupabaseStorage.
 * @return JSX element displaying the count of file attachments.
 */
function FileCount() {
  const { useSupabaseStorage } = require("@/hooks/use-supabase-storage");
  const { useFileAttachments } = useSupabaseStorage();
  const { data, isSuccess } = useFileAttachments();
  return <div aria-label="files">{isSuccess ? (data?.length || 0) : "-"}</div>;
}

describe("useSupabaseStorage", () => {
  it("lists attachments for current user", async () => {
    vi.doMock("@/lib/supabase/client", () => ({
      useSupabase: () => ({
        auth: {
          getUser: vi.fn(async () => ({ data: { user: { id: "u1" } } })),
          onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
        },
        from: vi.fn(() => ({
          select: vi.fn(() => ({
            eq: vi.fn(() => ({ order: vi.fn(async () => ({ data: [{ id: "a1" }], error: null })) })),
          })),
        })),
      }),
    }));

    const { findByLabelText } = render(<FileCount />);
    expect(await findByLabelText("files")).toHaveTextContent("1");
  });
});
