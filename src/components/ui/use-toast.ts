/**
 * @fileoverview Toast notification wrapper providing backward-compatible API
 * over Sonner. Maintains the same interface as the previous Radix-based toast.
 */

import type { ReactNode } from "react";
import { toast as sonnerToast } from "sonner";

type ToastVariant = "default" | "destructive";

/**
 * Props for creating a toast notification.
 */
interface ToastProps {
  /** Primary toast title */
  title?: ReactNode;
  /** Secondary description text */
  description?: ReactNode;
  /** Visual variant - "destructive" renders as error toast */
  variant?: ToastVariant;
  /** Optional action button */
  action?: {
    label: string;
    onClick: () => void;
  };
}

/**
 * Return value from toast() for controlling the notification.
 */
interface ToastReturn {
  /** Unique toast identifier */
  id: string | number;
  /** Dismiss this specific toast */
  dismiss: () => void;
  /** Update this toast with new props */
  update: (props: ToastProps) => void;
}

/**
 * Display a toast notification.
 *
 * Maps variant "destructive" to Sonner's error toast, otherwise uses default.
 *
 * @param props - Toast configuration
 * @returns Object with id, dismiss, and update functions
 *
 * @example
 * ```ts
 * // Success toast
 * toast({ title: "Saved", description: "Changes saved successfully" });
 *
 * // Error toast
 * toast({ title: "Error", description: "Failed to save", variant: "destructive" });
 * ```
 */
function toast(props: ToastProps): ToastReturn {
  const { title, description, variant, action } = props;

  const options = {
    action: action ? { label: action.label, onClick: action.onClick } : undefined,
    description,
  };

  let id: string | number;

  if (variant === "destructive") {
    id = sonnerToast.error(title ?? "", options);
  } else {
    id = sonnerToast(title ?? "", options);
  }

  return {
    dismiss: () => sonnerToast.dismiss(id),
    id,
    update: (next: ToastProps) => {
      sonnerToast.dismiss(id);
      toast(next);
    },
  };
}

/**
 * Hook providing toast state and control functions.
 *
 * Maintains backward compatibility with previous Radix-based implementation.
 * Note: Sonner manages its own internal state, so `toasts` array is always empty.
 *
 * @returns Object with toast function, dismiss function, and toasts array
 */
function useToast() {
  return {
    dismiss: (toastId?: string | number) => sonnerToast.dismiss(toastId),
    toast,
    toasts: [] as const, // Sonner manages its own state
  };
}

export { useToast, toast };
export type { ToastProps as Toast };
