/**
 * @fileoverview Recharts-based metrics visualization component.
 *
 * Displays time-series data as an area chart with gradient fill.
 * Uses ResponsiveContainer for fluid layouts.
 */

"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  // Generate unique gradient ID to avoid conflicts when multiple charts are rendered
  const gradientId = `gradient-${title.replace(/\s+/g, "-").toLowerCase()}`;

  return (
    <Card className={cn("", className)}>
      <CardHeader>
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer height={height} width="100%">
          <AreaChart data={data} margin={{ bottom: 0, left: 0, right: 10, top: 5 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.8} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid className="stroke-muted" strokeDasharray="3 3" />
            <XAxis className="text-xs" dataKey="name" />
            <YAxis className="text-xs" />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--background))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "6px",
              }}
            />
            <Area
              dataKey="value"
              fill={`url(#${gradientId})`}
              fillOpacity={1}
              stroke={color}
              type="monotone"
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
