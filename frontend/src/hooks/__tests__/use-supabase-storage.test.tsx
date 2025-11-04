/**
 * @fileoverview Tests for the useSupabaseStorage hook.
 */

import { waitFor } from "@testing-library/react";
import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSupabaseStorage } from "@/hooks/use-supabase-storage";
import type { FileAttachment } from "@/lib/supabase/database.types";
import { createMockSupabaseClient } from "@/test/mock-helpers.test";
import { render } from "@/test/test-utils.test";

const SUPABASE = createMockSupabaseClient();
const FROM_MOCK = SUPABASE.from as unknown as Mock;

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => SUPABASE,
  getBrowserClient: () => SUPABASE,
  useSupabase: () => SUPABASE,
}));

const CREATE_QUERY_BUILDER = (rows: FileAttachment[]) => {
  const result = { data: rows, error: null };
  const builder = {
    eq: vi.fn().mockImplementation((column: string, value: unknown) => {
      if (column === "user_id") {
        expect(value).toBe("mock-user-id");
      }
      return builder;
    }),
    order: vi.fn().mockImplementation(() => builder),
    select: vi.fn().mockReturnThis(),
    then: (
      onFulfilled?: (value: typeof result) => unknown,
      onRejected?: (reason: unknown) => unknown
    ) => Promise.resolve(result).then(onFulfilled, onRejected),
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
