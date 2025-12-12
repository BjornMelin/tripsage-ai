/**
 * @fileoverview Collapsible reasoning display for assistant messages.
 */

"use client";

import { ChevronDownIcon } from "lucide-react";
import { useState } from "react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import { Response } from "./response";
import { Shimmer } from "./shimmer";

export type ReasoningProps = {
  text: string;
  className?: string;
  defaultOpen?: boolean;
  isAnimating?: boolean;
};

export function Reasoning({
  text,
  className,
  defaultOpen = false,
  isAnimating = false,
}: ReasoningProps) {
  const [open, setOpen] = useState(defaultOpen);

  if (!text && !isAnimating) return null;

  return (
    <Collapsible
      className={cn(
        "my-2 rounded-md border border-yellow-300/50 dark:border-yellow-300/30",
        className
      )}
      onOpenChange={setOpen}
      open={open}
    >
      <CollapsibleTrigger asChild>
        <button
          className="flex w-full items-center justify-between gap-2 rounded-md bg-yellow-50 px-3 py-2 text-xs text-yellow-900 hover:bg-yellow-100 dark:bg-yellow-950 dark:text-yellow-200 dark:hover:bg-yellow-900/40"
          type="button"
        >
          <div className="flex items-center gap-2 font-medium">
            <ChevronDownIcon
              className={cn("size-3.5 transition-transform", open ? "rotate-180" : "")}
            />
            <span>Reasoning</span>
          </div>
          <span className="text-[10px] opacity-70">{open ? "Hide" : "Show"}</span>
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent className="border-t border-yellow-300/30 bg-yellow-50 px-3 py-2 text-xs text-yellow-900 dark:border-yellow-300/20 dark:bg-yellow-950 dark:text-yellow-200">
        {isAnimating && text.length === 0 ? (
          <Shimmer>Thinking…</Shimmer>
        ) : (
          <Response className="prose-sm" mode="static">
            {text}
          </Response>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}
