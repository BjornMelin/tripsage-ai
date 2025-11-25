/**
 * @fileoverview Single metric card component with value, label, and optional trend.
 *
 * Displays a single metric in a card format with support for trend indicators,
 * units, and descriptions.
 */

"use client";

import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * Props for the MetricsCard component.
 */
export interface MetricsCardProps {
  /** Title label for the metric */
  title: string;
  /** The metric value to display */
  value: number | string;
  /** Optional unit suffix (e.g., "ms", "%") */
  unit?: string;
  /** Optional trend direction */
  trend?: "up" | "down" | "neutral";
  /** Optional trend value text (e.g., "+5%") */
  trendValue?: string;
  /** Optional description text */
  description?: string;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Displays a single metric in a card format.
 *
 * @param props - Component props
 * @returns The rendered metrics card
 *
 * @example
 * ```tsx
 * <MetricsCard title="Total Requests" value={1000} />
 * <MetricsCard title="Latency" value={150} unit="ms" />
 * <MetricsCard title="Error Rate" value={5} unit="%" trend="up" trendValue="+2%" />
 * ```
 */
export function MetricsCard({
  title,
  value,
  unit,
  trend,
  trendValue,
  description,
  className,
}: MetricsCardProps) {
  const TrendIcon = trend === "up" ? ArrowUp : trend === "down" ? ArrowDown : Minus;

  const trendColor =
    trend === "up"
      ? "text-red-500"
      : trend === "down"
        ? "text-green-500"
        : "text-muted-foreground";

  return (
    <Card className={cn("", className)}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">
          {value}
          {unit && <span className="ml-1 text-sm font-normal">{unit}</span>}
        </div>
        {(trend || description) && (
          <div className="mt-1 flex items-center gap-1">
            {trend && <TrendIcon className={cn("h-3 w-3", trendColor)} />}
            {trendValue && (
              <span className={cn("text-xs", trendColor)}>{trendValue}</span>
            )}
            {description && (
              <span className="text-xs text-muted-foreground">{description}</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
