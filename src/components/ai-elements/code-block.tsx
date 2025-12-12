/**
 * @fileoverview Small code/output block with optional copy control.
 */

"use client";

import { CheckIcon, CopyIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type CodeBlockProps = {
  value: string;
  className?: string;
  isAnimating?: boolean;
  label?: string;
  maxHeightClassName?: string;
};

export function CodeBlock({
  value,
  className,
  isAnimating = false,
  label = "Output",
  maxHeightClassName = "max-h-96",
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const copiedTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const canCopy =
    typeof navigator !== "undefined" &&
    typeof navigator.clipboard?.writeText === "function";

  useEffect(() => {
    return () => {
      if (copiedTimeoutRef.current) {
        clearTimeout(copiedTimeoutRef.current);
        copiedTimeoutRef.current = null;
      }
    };
  }, []);

  const onCopy = useCallback(() => {
    if (!canCopy || isAnimating || value.length === 0) return;
    navigator.clipboard
      .writeText(value)
      .then(() => {
        setCopied(true);
        if (copiedTimeoutRef.current) {
          clearTimeout(copiedTimeoutRef.current);
          copiedTimeoutRef.current = null;
        }
        copiedTimeoutRef.current = setTimeout(() => {
          setCopied(false);
          copiedTimeoutRef.current = null;
        }, 1500);
      })
      .catch(() => undefined);
  }, [canCopy, isAnimating, value]);

  const copyAriaLabel = label ? `Copy ${label}` : "Copy";

  return (
    <div className={cn("rounded-md border bg-muted/30 text-xs", className)}>
      <div className="flex items-center justify-between border-b px-2 py-1">
        <div className="font-medium text-muted-foreground">{label}</div>
        <Button
          aria-label={copyAriaLabel}
          disabled={!canCopy || copied || isAnimating || value.length === 0}
          onClick={onCopy}
          size="icon-sm"
          variant="ghost"
        >
          {copied ? (
            <CheckIcon className="size-3.5" />
          ) : (
            <CopyIcon className="size-3.5" />
          )}
        </Button>
      </div>
      <pre
        className={cn(
          "overflow-x-auto overflow-y-auto whitespace-pre-wrap px-3 py-2 font-mono leading-relaxed",
          maxHeightClassName
        )}
      >
        {value}
      </pre>
    </div>
  );
}
