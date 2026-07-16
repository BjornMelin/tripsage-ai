/** @vitest-environment node */

import { convertToModelMessages, type UIMessage } from "ai";
import { describe, expect, it } from "vitest";
import { normalizeAndValidateImageAttachments } from "@/app/api/_helpers/attachments";
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

describe("normalizeAndValidateImageAttachments", () => {
  it("normalizes image media types before model-message conversion", async () => {
    const message = messageWithFile(" IMAGE/PNG ");

    expect(normalizeAndValidateImageAttachments([message])).toEqual({
      valid: true,
    });
    await expect(convertToModelMessages([message])).resolves.toEqual([
      {
        content: [
          {
            data: {
              type: "url",
              url: new URL("data:image/png;base64,AA=="),
            },
            filename: undefined,
            mediaType: "image/png",
            type: "file",
          },
        ],
        role: "user",
      },
    ]);
  });

  it("rejects non-image media types", () => {
    expect(
      normalizeAndValidateImageAttachments([messageWithFile("text/plain")])
    ).toEqual({
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

    expect(normalizeAndValidateImageAttachments([message])).toEqual({
      reason: "missing_media_type",
      valid: false,
    });
  });
});
