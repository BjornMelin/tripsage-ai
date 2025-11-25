/**
 * @fileoverview Composite dashboard metrics component.
 *
 * Displays a grid of metric cards with a time window selector.
 * Fetches data using useDashboardMetrics hook with automatic polling.
 */

"use client";

import type { TimeWindow } from "@schemas/dashboard";
import { AlertCircle } from "lucide-react";
import { useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useDashboardMetrics } from "@/hooks/use-dashboard-metrics";
import { MetricsCard } from "./metrics-card";

/**
 * Props for the DashboardMetrics component.
 */
export interface DashboardMetricsProps {
  /** Initial time window (default: "24h") */
  defaultWindow?: TimeWindow;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Composite component displaying dashboard metrics with time window selection.
 *
 * @param props - Component props
 * @returns The rendered dashboard metrics section
 *
 * @example
 * ```tsx
 * <DashboardMetrics defaultWindow="7d" />
 * ```
 */
export function DashboardMetrics({
  defaultWindow = "24h",
  className,
}: DashboardMetricsProps) {
  const [window, setWindow] = useState<TimeWindow>(defaultWindow);
  const { data, isLoading, isError, refetch } = useDashboardMetrics({ window });

  if (isLoading) {
    return <DashboardMetricsSkeleton />;
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription className="flex items-center gap-2">
          Failed to load metrics.
          <Button
            className="h-auto p-0 font-normal underline"
            onClick={() => refetch()}
            variant="link"
          >
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className={className}>
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold">System Metrics</h3>
        <Tabs onValueChange={(v) => setWindow(v as TimeWindow)} value={window}>
          <TabsList>
            <TabsTrigger value="24h">24h</TabsTrigger>
            <TabsTrigger value="7d">7d</TabsTrigger>
            <TabsTrigger value="30d">30d</TabsTrigger>
            <TabsTrigger value="all">All</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <MetricsCard
          title="Total Requests"
          value={data.totalRequests.toLocaleString()}
        />
        <MetricsCard
          title="Avg Latency"
          unit="ms"
          value={data.avgLatencyMs.toFixed(0)}
        />
        <MetricsCard
          title="Error Rate"
          trend={data.errorRate > 5 ? "up" : data.errorRate > 0 ? "neutral" : "down"}
          unit="%"
          value={data.errorRate.toFixed(1)}
        />
        <MetricsCard title="Total Trips" value={data.totalTrips} />
        <MetricsCard title="Active Trips" value={data.activeTrips} />
        <MetricsCard title="Completed Trips" value={data.completedTrips} />
      </div>
    </div>
  );
}

/**
 * Skeleton loading state for DashboardMetrics.
 */
function DashboardMetricsSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-9 w-48" />
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }, (_, i) => i + 1).map((key) => (
          <Skeleton className="h-24 w-full" key={key} />
        ))}
      </div>
    </div>
  );
}

export { DashboardMetricsSkeleton };
