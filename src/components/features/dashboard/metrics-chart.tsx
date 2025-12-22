/**
 * @fileoverview Recharts-based metrics visualization component.
 */

"use client";

import { useId } from "react";
import { WithRecharts } from "@/components/charts/chart-wrapper";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { cn } from "@/lib/utils";

/**
 * Data point for the metrics chart.
 */
export interface MetricsChartDataPoint {
  /** Label for the x-axis (e.g., time bucket name) */
  name: string;
  /** Numeric value for the y-axis */
  value: number;
}

/**
 * Props for the MetricsChart component.
 */
export interface MetricsChartProps {
  /** Chart title */
  title: string;
  /** Array of data points to visualize */
  data: MetricsChartDataPoint[];
  /** Primary color for the chart (default: "#8884d8") */
  color?: string;
  /** Chart height in pixels (default: 200) */
  height?: number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Displays time-series metrics data as an area chart.
 *
 * @param props - Component props
 * @returns The rendered chart card
 *
 * @example
 * ```tsx
 * <MetricsChart
 *   title="Request Volume"
 *   data={[
 *     { name: "Mon", value: 100 },
 *     { name: "Tue", value: 150 },
 *   ]}
 * />
 * ```
 */
export function MetricsChart({
  title,
  data,
  color = "#8884d8",
  height = 200,
  className,
}: MetricsChartProps) {
  // Generate unique gradient ID per instance to avoid collisions between charts
  const uniqueId = useId().replace(/[:]/g, "");
  const gradientId = `chart-gradient-${uniqueId}`;

  return (
    <Card className={cn(className)}>
      <CardHeader>
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <WithRecharts
          fallback={
            <div
              className="flex items-center justify-center"
              style={{ height, width: "100%" }}
            >
              <LoadingSpinner size="sm" />
            </div>
          }
        >
          {(Recharts) => (
            <Recharts.ResponsiveContainer height={height} width="100%">
              <Recharts.AreaChart
                data={data}
                margin={{ bottom: 0, left: 0, right: 10, top: 5 }}
              >
                <defs>
                  <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor={color} stopOpacity={0.8} />
                    <stop offset="95%" stopColor={color} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Recharts.CartesianGrid
                  className="stroke-muted"
                  strokeDasharray="3 3"
                />
                <Recharts.XAxis className="text-xs" dataKey="name" />
                <Recharts.YAxis className="text-xs" />
                <Recharts.Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--background))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "6px",
                  }}
                />
                <Recharts.Area
                  dataKey="value"
                  fill={`url(#${gradientId})`}
                  fillOpacity={1}
                  stroke={color}
                  type="monotone"
                />
              </Recharts.AreaChart>
            </Recharts.ResponsiveContainer>
          )}
        </WithRecharts>
      </CardContent>
    </Card>
  );
}
