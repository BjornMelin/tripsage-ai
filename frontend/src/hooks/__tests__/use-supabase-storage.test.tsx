/**
 * @fileoverview Tests for the useSupabaseStorage hook.
 */

import { waitFor } from "@testing-library/react";
import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSupabaseStorage } from "@/hooks/use-supabase-storage";
import type { FileAttachment } from "@/lib/supabase/database.types";
import { createMockSupabaseClient } from "@/test/mock-helpers";
import { render } from "@/test/test-utils";

const supabase = createMockSupabaseClient();
const fromMock = supabase.from as unknown as Mock;

vi.mock("@/lib/supabase/client", () => ({
  useSupabase: () => supabase,
  getBrowserClient: () => supabase,
  createClient: () => supabase,
}));

const createQueryBuilder = (rows: FileAttachment[]) => {
  const result = { data: rows, error: null };
  const builder = {
    select: vi.fn().mockReturnThis(),
    eq: vi.fn().mockImplementation((column: string, value: unknown) => {
      if (column === "user_id") {
        expect(value).toBe("mock-user-id");
      }
      return builder;
    }),
    order: vi.fn().mockImplementation(() => builder),
    then: (
      onFulfilled?: (value: typeof result) => unknown,
      onRejected?: (reason: unknown) => unknown
    ) => Promise.resolve(result).then(onFulfilled, onRejected),
  };
  return builder;
};

const createAttachment = (overrides: Partial<FileAttachment> = {}): FileAttachment => ({
  id: overrides.id ?? "attachment-1",
  user_id: overrides.user_id ?? "mock-user-id",
  trip_id: overrides.trip_id ?? null,
  chat_message_id: overrides.chat_message_id ?? null,
  filename: overrides.filename ?? "file.pdf",
  original_filename: overrides.original_filename ?? "file.pdf",
  file_size: overrides.file_size ?? 1024,
  mime_type: overrides.mime_type ?? "application/pdf",
  file_path: overrides.file_path ?? "mock/file.pdf",
  bucket_name: overrides.bucket_name ?? "attachments",
  upload_status: overrides.upload_status ?? "completed",
  virus_scan_status: overrides.virus_scan_status ?? "clean",
  virus_scan_result: overrides.virus_scan_result ?? {},
  metadata: overrides.metadata ?? {},
  created_at: overrides.created_at ?? new Date(0).toISOString(),
  updated_at: overrides.updated_at ?? new Date(0).toISOString(),
});

function FileCount() {
  const { useFileAttachments } = useSupabaseStorage();
  const { data, isSuccess } = useFileAttachments();
  return <div data-testid="files">{isSuccess ? (data?.length ?? 0) : "-"}</div>;
}

describe("useSupabaseStorage", () => {
  beforeEach(() => {
    fromMock.mockReset();
  });

  it("lists attachments for current user", async () => {
    const attachments = [createAttachment()];

    fromMock.mockImplementationOnce((table: string) => {
      expect(table).toBe("file_attachments");
      return createQueryBuilder(attachments);
    });

    const { getByTestId } = render(<FileCount />);

    await waitFor(() => {
      expect(getByTestId("files")).toHaveTextContent("1");
    });
  });
});
