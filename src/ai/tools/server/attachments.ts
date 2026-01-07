/**
 * @fileoverview Attachments listing tool for chat sessions (server-only).
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import { createToolError, TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import {
  attachmentsListToolInputSchema,
  attachmentsListToolOutputSchema,
  attachmentUploadStatusSchema,
} from "@schemas/attachments";
import { createServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const STORAGE_BUCKET = "attachments";
const SIGNED_URL_EXPIRATION_SECONDS = 3600;

/**
 * List attachments for a chat session (returns signed URLs).
 */
export const attachmentsList = createAiTool({
  description:
    "List attachments for a chat session and return signed URLs. " +
    "Use to see what files are available for the current chat.",
  execute: ({ chatId, limit }) =>
    withTelemetrySpan(
      "tools.attachments.list",
      { attributes: { chatId, limit } },
      async () => {
        const logger = createServerLogger("tools.attachments.list");
        const supabase = await createServerSupabase();

        const { data: rows, error } = await supabase
          .from("file_attachments")
          .select(
            "id, file_path, file_size, mime_type, original_filename, upload_status"
          )
          .eq("chat_id", chatId)
          .order("created_at", { ascending: false })
          .limit(limit);

        if (error) {
          throw createToolError(TOOL_ERROR_CODES.toolExecutionFailed, error.message, {
            chatId,
          });
        }

        const attachments = rows ?? [];
        const paths = attachments
          .map((row) => row.file_path)
          .filter(
            (path): path is string => typeof path === "string" && path.length > 0
          );

        const urlMap = new Map<string, string>();
        if (paths.length > 0) {
          const { data: signedData, error: signedError } = await supabase.storage
            .from(STORAGE_BUCKET)
            .createSignedUrls(paths, SIGNED_URL_EXPIRATION_SECONDS, { download: true });

          if (signedError) {
            throw createToolError(
              TOOL_ERROR_CODES.toolExecutionFailed,
              signedError.message,
              {
                chatId,
              }
            );
          }

          for (const entry of signedData ?? []) {
            if (
              entry &&
              typeof entry.path === "string" &&
              typeof entry.signedUrl === "string" &&
              entry.signedUrl &&
              !entry.error
            ) {
              urlMap.set(entry.path, entry.signedUrl);
            }
          }
        }

        const items = attachments
          .map((att) => {
            if (!att.file_path) {
              logger.warn("Missing file_path for attachment", {
                attachmentId: att.id,
                chatId,
              });
              return null;
            }

            const url = urlMap.get(att.file_path);
            if (!url) {
              logger.warn("Missing signed URL for attachment", {
                attachmentId: att.id,
                chatId,
                filePath: att.file_path,
              });
              return null;
            }

            const uploadStatus = attachmentUploadStatusSchema.safeParse(
              att.upload_status
            );
            if (!uploadStatus.success) {
              logger.warn("Invalid attachment upload status", {
                attachmentId: att.id,
                chatId,
                uploadStatus: att.upload_status,
              });
              return null;
            }

            return {
              id: att.id,
              mimeType: att.mime_type,
              originalName: att.original_filename,
              size: att.file_size,
              uploadStatus: uploadStatus.data,
              url,
            };
          })
          .filter((item): item is NonNullable<typeof item> => item !== null);

        return { items };
      }
    ),
  inputSchema: attachmentsListToolInputSchema,
  name: "attachments.list",
  outputSchema: attachmentsListToolOutputSchema,
  validateOutput: true,
});
