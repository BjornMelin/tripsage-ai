/**
 * @fileoverview Chart wrapper component for dynamically importing Recharts components to reduce initial bundle size.
 */
"use client";

import dynamic from "next/dynamic";
import type { ComponentProps, ComponentType } from "react";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

/** Type-safe dynamic import wrapper for Recharts components */
const CreateDynamicComponent = <P extends object>(
  importFunc: () => Promise<{ default: ComponentType<P> } | ComponentType<P>>
) => {
  return dynamic(
    async () => {
      const component = await importFunc();
      // Handle both default export and named export patterns
      return typeof component === "function" ? component : component.default;
    },
    { ssr: false }
  );
};

/** Dynamically import chart components to reduce initial bundle size */
export const responsiveContainer = dynamic(
  () => import("recharts").then((mod) => mod.ResponsiveContainer),
  {
    loading: () => (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="sm" />
      </div>
    ),
    ssr: false,
  }
);

export const areaChart = dynamic(
  () => import("recharts").then((mod) => mod.AreaChart),
  { ssr: false }
);

export const lineChart = dynamic(
  () => import("recharts").then((mod) => mod.LineChart),
  { ssr: false }
);

/** Use the safe dynamic wrapper for problematic components */
export const area = CreateDynamicComponent(() =>
  import("recharts").then(
    (mod) => mod.Area as unknown as React.ComponentType<Record<string, unknown>>
  )
);

export const line = CreateDynamicComponent(() =>
  import("recharts").then(
    (mod) => mod.Line as unknown as React.ComponentType<Record<string, unknown>>
  )
);

export const cartesianGrid = dynamic(
  () => import("recharts").then((mod) => mod.CartesianGrid),
  { ssr: false }
);

export const xAxis = CreateDynamicComponent(() =>
  import("recharts").then(
    (mod) => mod.XAxis as unknown as React.ComponentType<Record<string, unknown>>
  )
);

export const yAxis = CreateDynamicComponent(() =>
  import("recharts").then(
    (mod) => mod.YAxis as unknown as React.ComponentType<Record<string, unknown>>
  )
);

export const tooltip = CreateDynamicComponent(() =>
  import("recharts").then(
    (mod) => mod.Tooltip as unknown as React.ComponentType<Record<string, unknown>>
  )
);

/** Export types for better TypeScript support */
export type ResponsiveContainerProps = ComponentProps<typeof responsiveContainer>;
export type AreaChartProps = ComponentProps<typeof areaChart>;
export type LineChartProps = ComponentProps<typeof lineChart>;
export type AreaProps = ComponentProps<typeof area>;
export type LineProps = ComponentProps<typeof line>;
export type CartesianGridProps = ComponentProps<typeof cartesianGrid>;
export type XaxisProps = ComponentProps<typeof xAxis>;
export type YaxisProps = ComponentProps<typeof yAxis>;
export type TooltipProps = ComponentProps<typeof tooltip>;
