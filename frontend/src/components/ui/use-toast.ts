/**
 * @fileoverview Toast state manager inspired by react-hot-toast. Provides a
 * small reducer, timeouts, and helpers for showing/dismissing toasts.
 */
// Inspired by react-hot-toast library
import * as React from "react";

import type { ToastActionElement, ToastProps } from "@/components/ui/toast";

const TOAST_LIMIT = 5;
const TOAST_REMOVE_DELAY = 5000;

type ToasterToast = ToastProps & {
  id: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: ToastActionElement;
};

const ACTION_TYPES = {
  addToast: "ADD_TOAST",
  dismissToast: "DISMISS_TOAST",
  removeToast: "REMOVE_TOAST",
  updateToast: "UPDATE_TOAST",
} as const;

let count = 0;

function genId() {
  count = (count + 1) % Number.MAX_SAFE_INTEGER;
  return count.toString();
}

type ActionType = typeof ACTION_TYPES;

type Action =
  | {
      type: ActionType["addToast"];
      toast: ToasterToast;
    }
  | {
      type: ActionType["updateToast"];
      toast: Partial<ToasterToast>;
    }
  | {
      type: ActionType["dismissToast"];
      toastId?: string;
    }
  | {
      type: ActionType["removeToast"];
      toastId?: string;
    };

interface State {
  toasts: ToasterToast[];
}

const TOAST_TIMEOUTS = new Map<string, NodeJS.Timeout>();

const ADD_TO_REMOVE_QUEUE = (toastId: string) => {
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

const LISTENERS: Array<(state: State) => void> = [];

let memoryState: State = { toasts: [] };

function dispatch(action: Action) {
  memoryState = reducer(memoryState, action);
  LISTENERS.forEach((listener) => {
    listener(memoryState);
  });
}

type Toast = Omit<ToasterToast, "id">;

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
      onOpenChange: (open) => {
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
