/**
 * @fileoverview Notifications slice for UI store.
 */

import { notificationSchema } from "@schemas/stores";
import type { StateCreator } from "zustand";
import { nowIso, secureId } from "@/lib/security/random";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import type { NotificationsSlice, UiState } from "./types";

const logger = createStoreLogger({ storeName: "ui" });

const GENERATE_ID = () => secureId(12);
const GET_CURRENT_TIMESTAMP = () => nowIso();

// Map to store timeout IDs keyed by notification ID
const notificationTimeouts = new Map<string, NodeJS.Timeout>();

export const createNotificationsSlice: StateCreator<
  UiState,
  [],
  [],
  NotificationsSlice
> = (set, get) => ({
  addNotification: (notification) => {
    const id = GENERATE_ID();
    const result = notificationSchema.safeParse({
      ...notification,
      createdAt: GET_CURRENT_TIMESTAMP(),
      id,
      isRead: notification.isRead ?? false,
    });

    if (result.success) {
      set((state) => ({
        notifications: [result.data, ...state.notifications].slice(0, 50), // Keep max 50 notifications
      }));

      // Auto-remove notification if duration is specified
      if (notification.duration) {
        const timeoutId = setTimeout(() => {
          get().removeNotification(id);
        }, notification.duration);
        notificationTimeouts.set(id, timeoutId);
      }

      return id;
    }
    logger.error("Invalid notification", {
      error: result.error,
      errorMessage: result.error.message,
      issues: result.error.issues.map((issue) => ({
        message: issue.message,
        path: issue.path.join("."),
      })),
    });
    return "";
  },

  clearAllNotifications: () => {
    // Clear all pending timeouts
    notificationTimeouts.forEach((timeoutId) => {
      clearTimeout(timeoutId);
    });
    notificationTimeouts.clear();
    set({ notifications: [] });
  },

  markNotificationAsRead: (id) => {
    set((state) => ({
      notifications: state.notifications.map((n) =>
        n.id === id ? { ...n, isRead: true } : n
      ),
    }));
  },
  notifications: [],

  removeNotification: (id) => {
    // Clear the associated timeout if it exists
    const timeoutId = notificationTimeouts.get(id);
    if (timeoutId) {
      clearTimeout(timeoutId);
      notificationTimeouts.delete(id);
    }

    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    }));
  },

  // unreadNotificationCount is defined as a computed getter in the main store composition
  unreadNotificationCount: 0,
});
