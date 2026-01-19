/**
 * @fileoverview Collapsible tool call/result display.
 */

"use client";

import { ChevronDownIcon } from "lucide-react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import { CodeBlock } from "./code-block";

export type ToolProps = {
  name: string;
  status?: string;
  input?: unknown;
  output?: unknown;
  providerMetadata?: unknown;
  className?: string;
  defaultOpen?: boolean;
};

function formatValue(value: unknown): string {
  if (value === undefined) return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function Tool({
  name,
  status,
  input,
  output,
  providerMetadata,
  className,
  defaultOpen = false,
}: ToolProps) {
  const [open, setOpen] = useState(defaultOpen);
  const hasInput = input !== undefined;
  const hasOutput = output !== undefined;
  const hasProviderMetadata = providerMetadata !== undefined;

  const badgeVariant = useMemo(() => {
    if (!status) return "secondary" as const;
    const lower = status.toLowerCase();
    if (lower.includes("error") || lower.includes("failed")) {
      return "destructive" as const;
    }
    return "secondary" as const;
  }, [status]);

  return (
    <Collapsible
      className={cn("my-2 rounded-md border bg-muted/30 text-xs", className)}
      onOpenChange={setOpen}
      open={open}
    >
      <CollapsibleTrigger asChild>
        <button
          className="flex w-full items-center justify-between gap-2 px-3 py-2 hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          type="button"
        >
          <div className="flex items-center gap-2">
            <ChevronDownIcon
              className={cn("size-3.5 transition-transform", open ? "rotate-180" : "")}
              aria-hidden="true"
            />
            <span className="font-medium">{name}</span>
            {status ? (
              <Badge className="text-[10px]" variant={badgeVariant}>
                {status}
              </Badge>
            ) : null}
          </div>
          <span className="text-[10px] opacity-70">{open ? "Hide" : "Show"}</span>
        </button>
      </CollapsibleTrigger>
      {hasInput || hasOutput || hasProviderMetadata ? (
        <CollapsibleContent className="space-y-2 border-t px-3 py-2">
          {open && hasInput ? (
            <CodeBlock label="Input" value={formatValue(input)} />
          ) : null}
          {open && hasOutput ? (
            <CodeBlock label="Output" value={formatValue(output)} />
          ) : null}
          {open && hasProviderMetadata ? (
            <CodeBlock
              label="Provider metadata"
              value={formatValue(providerMetadata)}
            />
          ) : null}
        </CollapsibleContent>
      ) : null}
    </Collapsible>
  );
}
