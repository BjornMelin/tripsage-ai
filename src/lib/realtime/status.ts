/**
 * @fileoverview Shared realtime status types and helpers.
 */

import type { ConnectionStatus } from "@schemas/realtime";

/**
 * Maps low-level Supabase channel states to the app-level connection status.
 */
export function mapChannelStateToStatus(
  state: "idle" | "connecting" | "subscribed" | "error" | "closed",
  hasError: boolean
): ConnectionStatus {
  if (hasError) return "error";
  switch (state) {
    case "subscribed":
      return "connected";
    case "connecting":
      return "connecting";
    case "idle":
    case "closed":
      return "disconnected";
    default:
      return "error";
  }
}

/**
 * Human-friendly label for rendering connection status.
 */
export function formatConnectionStatus(status: ConnectionStatus): string {
  switch (status) {
    case "connected":
      return "Connected";
    case "connecting":
      return "Connecting";
    case "reconnecting":
      return "Reconnecting";
    case "disconnected":
      return "Disconnected";
    default:
      return "Error";
  }
}
