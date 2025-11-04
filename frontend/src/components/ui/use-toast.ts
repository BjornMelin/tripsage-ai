/**
 * @fileoverview Toast state manager inspired by react-hot-toast. Provides a
 * small reducer, timeouts, and helpers for showing/dismissing toasts.
 */

// Inspired by react-hot-toast library
import * as React from "react";

import type { ToastActionElement, ToastProps } from "@/components/ui/toast";

// Maximum number of toasts to display simultaneously.
const TOAST_LIMIT = 5;

// Delay in milliseconds before removing a dismissed toast from the DOM.
const TOAST_REMOVE_DELAY = 5000;

/**
 * Internal toast representation with additional properties for state management.
 */
type ToasterToast = ToastProps & {
  // Unique identifier for the toast.
  id: string;
  // Optional title content for the toast.
  title?: React.ReactNode;
  // Optional description content for the toast.
  description?: React.ReactNode;
  // Optional action element to display in the toast.
  action?: ToastActionElement;
};

// Action type constants for toast state management.
const ACTION_TYPES = {
  addToast: "ADD_TOAST",
  dismissToast: "DISMISS_TOAST",
  removeToast: "REMOVE_TOAST",
  updateToast: "UPDATE_TOAST",
} as const;

// Global counter for generating unique toast IDs.
let count = 0;

/**
 * Generates a unique ID for toasts using a global counter.
 *
 * @returns A string representation of the unique ID.
 */
function genId(): string {
  count = (count + 1) % Number.MAX_SAFE_INTEGER;
  return count.toString();
}

// Type alias for the action types object.
type ActionType = typeof ACTION_TYPES;

/**
 * Union type representing all possible actions that can be dispatched
 * to the toast reducer.
 */
type Action =
  | {
      // Action type for adding a new toast.
      type: ActionType["addToast"];
      // The toast to add.
      toast: ToasterToast;
    }
  | {
      // Action type for updating an existing toast.
      type: ActionType["updateToast"];
      // Partial toast properties to update.
      toast: Partial<ToasterToast>;
    }
  | {
      // Action type for dismissing a toast (or all toasts).
      type: ActionType["dismissToast"];
      // Optional ID of the toast to dismiss. If undefined, dismisses all toasts.
      toastId?: string;
    }
  | {
      // Action type for removing a toast from the DOM (or all toasts).
      type: ActionType["removeToast"];
      // Optional ID of the toast to remove. If undefined, removes all toasts.
      toastId?: string;
    };

/**
 * State interface for the toast reducer.
 */
interface State {
  // Array of active toasts.
  toasts: ToasterToast[];
}

// Map of toast IDs to their removal timeouts for cleanup.
const TOAST_TIMEOUTS = new Map<string, NodeJS.Timeout>();

/**
 * Schedules a toast for removal from the DOM after the dismissal delay.
 * Prevents duplicate timeouts for the same toast ID.
 *
 * @param toastId - The ID of the toast to queue for removal.
 */
const ADD_TO_REMOVE_QUEUE = (toastId: string): void => {
  if (TOAST_TIMEOUTS.has(toastId)) {
    return;
  }

  const timeout = setTimeout(() => {
    TOAST_TIMEOUTS.delete(toastId);
    dispatch({
      toastId: toastId,
      type: ACTION_TYPES.removeToast,
    });
  }, TOAST_REMOVE_DELAY);

  TOAST_TIMEOUTS.set(toastId, timeout);
};

/**
 * Reducer function for managing toast state. Handles adding, updating,
 * dismissing, and removing toasts.
 *
 * @param state - The current toast state.
 * @param action - The action to apply to the state.
 * @returns The new state after applying the action.
 */
export const reducer = (state: State, action: Action): State => {
  switch (action.type) {
    case ACTION_TYPES.addToast:
      return {
        ...state,
        toasts: [action.toast, ...state.toasts].slice(0, TOAST_LIMIT),
      };

    case ACTION_TYPES.updateToast:
      return {
        ...state,
        toasts: state.toasts.map((t) =>
          t.id === action.toast.id ? { ...t, ...action.toast } : t
        ),
      };

    case ACTION_TYPES.dismissToast: {
      const { toastId } = action;

      // ! Side effects ! - This could be extracted into a dismissToast() action,
      // but I'll keep it here for simplicity
      if (toastId) {
        ADD_TO_REMOVE_QUEUE(toastId);
      } else {
        state.toasts.forEach((toast) => {
          ADD_TO_REMOVE_QUEUE(toast.id);
        });
      }

      return {
        ...state,
        toasts: state.toasts.map((t) =>
          t.id === toastId || toastId === undefined
            ? {
                ...t,
                open: false,
              }
            : t
        ),
      };
    }
    case ACTION_TYPES.removeToast:
      if (action.toastId === undefined) {
        return {
          ...state,
          toasts: [],
        };
      }
      return {
        ...state,
        toasts: state.toasts.filter((t) => t.id !== action.toastId),
      };
  }
};

// Array of listener functions that are notified when state changes.
const LISTENERS: Array<(state: State) => void> = [];

// In-memory state that serves as the single source of truth for toasts.
let memoryState: State = { toasts: [] };

/**
 * Dispatches an action to update the toast state and notifies all listeners.
 *
 * @param action - The action to dispatch to the reducer.
 */
function dispatch(action: Action): void {
  memoryState = reducer(memoryState, action);
  LISTENERS.forEach((listener) => {
    listener(memoryState);
  });
}

/**
 * Props for creating a new toast, excluding the auto-generated ID.
 */
type Toast = Omit<ToasterToast, "id">;

/**
 * Creates and displays a new toast notification.
 *
 * @param props - The properties for the toast (excluding ID).
 * @returns An object with methods to dismiss or update the toast.
 */
function toast({ ...props }: Toast) {
  const id = genId();

  const update = (props: ToasterToast) =>
    dispatch({
      toast: { ...props, id },
      type: ACTION_TYPES.updateToast,
    });
  const dismiss = () => dispatch({ toastId: id, type: ACTION_TYPES.dismissToast });

  dispatch({
    toast: {
      ...props,
      id,
      onOpenChange: (open: boolean) => {
        if (!open) dismiss();
      },
      open: true,
    },
    type: ACTION_TYPES.addToast,
  });

  return {
    dismiss,
    id: id,
    update,
  };
}

/**
 * React hook for accessing toast state and actions.
 * Provides the current toasts, a function to show new toasts,
 * and a function to dismiss toasts.
 *
 * @returns An object containing the current toast state and control functions.
 */
function useToast() {
  const [state, setState] = React.useState<State>(memoryState);

  React.useEffect(() => {
    LISTENERS.push(setState);
    return () => {
      const index = LISTENERS.indexOf(setState);
      if (index > -1) {
        LISTENERS.splice(index, 1);
      }
    };
  }, []);

  return {
    ...state,
    dismiss: (toastId?: string) =>
      dispatch({ toastId, type: ACTION_TYPES.dismissToast }),
    toast,
  };
}

export { useToast, toast };
export type { Toast };
