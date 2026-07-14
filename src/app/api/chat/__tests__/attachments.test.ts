/**
 * @fileoverview Unit tests for UI image attachment validation.
 */

import type { UIMessage } from "ai";
import { describe, expect, it } from "vitest";
import { validateImageAttachments } from "@/app/api/_helpers/attachments";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

function messageWithFile(mediaType: string): UIMessage {
  return {
    id: "message-1",
    parts: [
      {
        mediaType,
        type: "file",
        url: "data:image/png;base64,AA==",
      },
    ],
    role: "user",
  };
}

describe("validateImageAttachments", () => {
  it("accepts image media types case-insensitively", () => {
    expect(validateImageAttachments([messageWithFile(" IMAGE/PNG ")])).toEqual({
      valid: true,
    });
  });

  it("rejects non-image media types", () => {
    expect(validateImageAttachments([messageWithFile("text/plain")])).toEqual({
      reason: "unsupported_media_type",
      valid: false,
    });
  });

  it("rejects file parts without a media type", () => {
    const message = unsafeCast<UIMessage>({
      id: "message-1",
      parts: [{ type: "file", url: "data:image/png;base64,AA==" }],
      role: "user",
    });

    expect(validateImageAttachments([message])).toEqual({
      reason: "missing_media_type",
      valid: false,
    });
  });
});
