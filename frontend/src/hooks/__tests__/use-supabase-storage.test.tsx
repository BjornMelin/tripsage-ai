/** @vitest-environment jsdom */

import { waitFor } from "@testing-library/react";
import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSupabaseStorage } from "@/hooks/use-supabase-storage";
import type { FileAttachment } from "@/lib/supabase/database.types";
import { createMockSupabaseClient } from "@/test/mocks/supabase";
import { render } from "@/test/test-utils";

const SUPABASE = createMockSupabaseClient();
const FROM_MOCK = SUPABASE.from as unknown as Mock;

// Mock auth.getUser to return a user
SUPABASE.auth = {
  ...SUPABASE.auth,
  getUser: vi.fn().mockResolvedValue({
    data: { user: { id: "mock-user-id" } },
    error: null,
  }),
  onAuthStateChange: vi.fn().mockReturnValue({
    data: {
      subscription: {
        unsubscribe: vi.fn(),
      },
    },
  }),
} as unknown as typeof SUPABASE.auth;

vi.mock("@/lib/supabase", () => ({
  createClient: () => SUPABASE,
  getBrowserClient: () => SUPABASE,
  useSupabase: () => SUPABASE,
  useSupabaseRequired: () => SUPABASE,
}));

const CREATE_QUERY_BUILDER = (rows: FileAttachment[]) => {
  const result = { data: rows, error: null };

  // Create a mock builder that behaves like a Promise
  const builder = {
    eq: vi.fn().mockImplementation((column: string, value: unknown) => {
      if (column === "user_id") {
        expect(value).toBe("mock-user-id");
      }
      return CREATE_QUERY_BUILDER(rows);
    }),
    order: vi.fn().mockImplementation(() => CREATE_QUERY_BUILDER(rows)),
    select: vi.fn().mockReturnThis(),
    // biome-ignore lint/suspicious/noThenProperty: Mock needs Promise-like then method
    then: vi
      .fn()
      .mockImplementation((onFulfilled: (value: typeof result) => unknown) =>
        Promise.resolve(result).then(onFulfilled)
      ),
  };

  return builder;
};

const CREATE_ATTACHMENT = (
  overrides: Partial<FileAttachment> = {}
): FileAttachment => ({
  bucket_name: overrides.bucket_name ?? "attachments",
  chat_message_id: overrides.chat_message_id ?? null,
  created_at: overrides.created_at ?? new Date(0).toISOString(),
  file_path: overrides.file_path ?? "mock/file.pdf",
  file_size: overrides.file_size ?? 1024,
  filename: overrides.filename ?? "file.pdf",
  id: overrides.id ?? "attachment-1",
  metadata: overrides.metadata ?? {},
  mime_type: overrides.mime_type ?? "application/pdf",
  original_filename: overrides.original_filename ?? "file.pdf",
  trip_id: overrides.trip_id ?? null,
  updated_at: overrides.updated_at ?? new Date(0).toISOString(),
  upload_status: overrides.upload_status ?? "completed",
  user_id: overrides.user_id ?? "mock-user-id",
  virus_scan_result: overrides.virus_scan_result ?? {},
  virus_scan_status: overrides.virus_scan_status ?? "clean",
});

function FileCount() {
  const { useFileAttachments } = useSupabaseStorage();
  const { data, isSuccess } = useFileAttachments();
  return <div data-testid="files">{isSuccess ? (data?.length ?? 0) : "-"}</div>;
}

describe("useSupabaseStorage", () => {
  beforeEach(() => {
    vi.useRealTimers();
    FROM_MOCK.mockReset();
  });

  it("lists attachments for current user", async () => {
    const attachments = [CREATE_ATTACHMENT()];

    FROM_MOCK.mockImplementationOnce((table: string) => {
      expect(table).toBe("file_attachments");
      return CREATE_QUERY_BUILDER(attachments);
    });

    const { getByTestId } = render(<FileCount />);

    await waitFor(() => {
      expect(getByTestId("files")).toHaveTextContent("1");
    });
  });
});
