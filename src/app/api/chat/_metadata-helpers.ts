/**
 * @fileoverview Shared helpers for reading chat message metadata.
 */

export function isJsonObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function getStringFromMetadata(
  metadata: unknown,
  key: string
): string | undefined {
  if (!isJsonObject(metadata)) return undefined;
  const value = metadata[key];
  return typeof value === "string" && value.trim().length > 0
    ? value.trim()
    : undefined;
}

export function isSupersededMessage(metadata: unknown): boolean {
  const supersededBy = getStringFromMetadata(metadata, "supersededBy");
  if (supersededBy) return true;
  return getStringFromMetadata(metadata, "status") === "superseded";
}

export function getUiMessageIdFromRow(row: { id: number; metadata: unknown }): string {
  const uiMessageId = getStringFromMetadata(row.metadata, "uiMessageId");
  return uiMessageId ?? `db:${row.id}`;
}
