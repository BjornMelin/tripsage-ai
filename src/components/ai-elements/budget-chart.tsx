/**
 * @fileoverview Budget plan chart component for AI Elements.
 */

"use client";

import type { BudgetPlanResult } from "@schemas/agents";
import type { ComponentProps } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Source, Sources, SourcesContent, SourcesTrigger } from "./sources";

/**
 * Props for BudgetChart component.
 */
export type BudgetChartProps = ComponentProps<typeof Card> & {
  /** Budget plan result to render. */
  result: BudgetPlanResult;
};

type BudgetAllocation = BudgetPlanResult["allocations"][number];

/**
 * Render a budget plan with category allocations and tips.
 */
export function BudgetChart({ result, ...props }: BudgetChartProps) {
  const allocations: BudgetAllocation[] = result.allocations ?? [];
  const total = allocations.reduce(
    (sum: number, allocation: BudgetAllocation) => sum + allocation.amount,
    0
  );
  const currency = result.currency ?? "USD";

  return (
    <Card {...props}>
      <CardHeader>
        <CardTitle>Budget Plan</CardTitle>
        <CardDescription>
          {allocations.length} categories · Total{" "}
          {new Intl.NumberFormat(undefined, {
            currency,
            style: "currency",
          }).format(total)}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {allocations.map((allocation: BudgetAllocation, index: number) => {
            const percentage =
              total > 0 ? Math.round((allocation.amount / total) * 100) : 0;
            return (
              <div key={`${allocation.category}-${index}`} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{allocation.category}</span>
                  <span className="font-semibold">
                    {new Intl.NumberFormat(undefined, {
                      currency,
                      style: "currency",
                    }).format(allocation.amount)}
                  </span>
                </div>
                <div className="h-2 rounded-full bg-muted">
                  <div
                    className="h-2 rounded-full bg-primary"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                {allocation.rationale ? (
                  <p className="text-xs opacity-80">{allocation.rationale}</p>
                ) : null}
              </div>
            );
          })}
        </div>
        {Array.isArray(result.tips) && result.tips.length > 0 ? (
          <div className="mt-4 space-y-1 rounded border p-3">
            <div className="text-sm font-medium">Tips</div>
            <ul className="list-disc space-y-1 pl-5 text-xs opacity-80">
              {result.tips.map((tip: string) => (
                <li key={tip}>{tip}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {Array.isArray(result.sources) && result.sources.length > 0 ? (
          <div className="mt-3">
            <Sources>
              <SourcesTrigger count={result.sources.length} />
              <SourcesContent>
                <div className="space-y-1">
                  {result.sources.map((source) => (
                    <Source key={source.url} href={source.url}>
                      {source.title ?? source.url}
                    </Source>
                  ))}
                </div>
              </SourcesContent>
            </Sources>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
