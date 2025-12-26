/**
 * @fileoverview Clipboard helpers with fallbacks for older browsers. Must only be imported in client components.
 */

"use client";

export type ClipboardCopyResult =
  | { ok: true; method: "clipboard" | "fallback" }
  | {
      ok: false;
      reason: "permission-denied" | "insecure-context" | "unavailable" | "failed";
      error?: unknown;
    };

function copyTextWithExecCommand(text: string): boolean {
  if (typeof document === "undefined") return false;

  try {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    textarea.style.top = "0";
    document.body.appendChild(textarea);
    textarea.select();
    const success = document.execCommand("copy");
    document.body.removeChild(textarea);
    return success;
  } catch {
    return false;
  }
}

/**
 * Toast function type for clipboard feedback.
 */
type ToastFn = (opts: {
  description: string;
  title: string;
  variant?: "default" | "destructive";
}) => void;

/**
 * Standard toast messages for clipboard copy results.
 */
export interface CopyToastMessages {
  /** Toast shown on successful copy. */
  success: { title: string; description: string };
  /** Toast shown when clipboard permission is denied. */
  permissionDenied?: { title: string; description: string };
  /** Toast shown in insecure contexts (non-HTTPS). */
  insecureContext?: { title: string; description: string };
  /** Toast shown when clipboard API is unavailable. */
  unavailable?: { title: string; description: string };
  /** Toast shown on generic copy failure. */
  failed?: { title: string; description: string };
}

const DEFAULT_TOAST_MESSAGES: Required<CopyToastMessages> = {
  failed: {
    description: "Unable to copy. Please copy it manually.",
    title: "Copy Failed",
  },
  insecureContext: {
    description: "Clipboard access is only available in secure contexts (HTTPS).",
    title: "Clipboard Unavailable",
  },
  permissionDenied: {
    description: "Clipboard permission denied. Please allow access and try again.",
    title: "Permission Required",
  },
  success: {
    description: "Copied to clipboard",
    title: "Copied",
  },
  unavailable: {
    description: "Clipboard API unavailable. Please copy it manually.",
    title: "Copy Failed",
  },
};

/**
 * Copies text to clipboard and shows appropriate toast feedback.
 *
 * @param text - Text to copy to clipboard
 * @param toast - Toast function from useToast hook
 * @param messages - Optional custom toast messages (merged with defaults)
 * @returns The clipboard copy result
 *
 * @example
 * ```tsx
 * const { toast } = useToast();
 * const result = await copyToClipboardWithToast(shareUrl, toast, {
 *   success: { title: "Link Copied", description: "Share link copied to clipboard" }
 * });
 * ```
 */
export async function copyToClipboardWithToast(
  text: string,
  toast: ToastFn,
  messages?: Partial<CopyToastMessages>
): Promise<ClipboardCopyResult> {
  const msgs = { ...DEFAULT_TOAST_MESSAGES, ...messages };
  const result = await copyTextToClipboard(text);

  if (result.ok) {
    toast({ ...msgs.success });
    return result;
  }

  switch (result.reason) {
    case "permission-denied":
      toast({ ...msgs.permissionDenied, variant: "destructive" });
      break;
    case "insecure-context":
      toast({ ...msgs.insecureContext, variant: "destructive" });
      break;
    case "unavailable":
      toast({ ...msgs.unavailable, variant: "destructive" });
      break;
    case "failed":
      toast({ ...msgs.failed, variant: "destructive" });
      if (process.env.NODE_ENV === "development" && result.error) {
        console.error("Clipboard copy failed:", result.error);
      }
      break;
    default: {
      const _exhaustiveCheck: never = result.reason;
      return _exhaustiveCheck;
    }
  }

  return result;
}

export async function copyTextToClipboard(text: string): Promise<ClipboardCopyResult> {
  const canUseClipboardApi =
    typeof navigator !== "undefined" &&
    typeof navigator.clipboard?.writeText === "function";

  if (canUseClipboardApi) {
    try {
      await navigator.clipboard.writeText(text);
      return { method: "clipboard", ok: true };
    } catch (error) {
      if (error instanceof Error && error.name === "NotAllowedError") {
        return { error, ok: false, reason: "permission-denied" };
      }
      if (error instanceof Error && error.name === "SecurityError") {
        return { error, ok: false, reason: "insecure-context" };
      }

      const fallbackSuccess = copyTextWithExecCommand(text);
      if (fallbackSuccess) return { method: "fallback", ok: true };
      return { error, ok: false, reason: "failed" };
    }
  }

  const fallbackSuccess = copyTextWithExecCommand(text);
  if (fallbackSuccess) return { method: "fallback", ok: true };
  return { ok: false, reason: "unavailable" };
}
