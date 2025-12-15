/**
 * @fileoverview Clipboard helpers with fallbacks for older browsers.
 * Must only be imported in client components.
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
