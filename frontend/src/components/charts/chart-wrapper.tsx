"use client";

import { LoadingSpinner } from "@/components/ui/loading-spinner";
import dynamic from "next/dynamic";
import type { ComponentProps, ComponentType } from "react";

// Type-safe dynamic import wrapper for Recharts components
const createDynamicComponent = <P extends object>(
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

// Dynamically import chart components to reduce initial bundle size
export const ResponsiveContainer = dynamic(
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

export const AreaChart = dynamic(
  () => import("recharts").then((mod) => mod.AreaChart),
  { ssr: false }
);

export const LineChart = dynamic(
  () => import("recharts").then((mod) => mod.LineChart),
  { ssr: false }
);

// Use the safe dynamic wrapper for problematic components
export const Area = createDynamicComponent(() =>
  import("recharts").then((mod) => mod.Area as any)
);

export const Line = createDynamicComponent(() =>
  import("recharts").then((mod) => mod.Line as any)
);

export const CartesianGrid = dynamic(
  () => import("recharts").then((mod) => mod.CartesianGrid),
  { ssr: false }
);

export const XAxis = createDynamicComponent(() =>
  import("recharts").then((mod) => mod.XAxis as any)
);

export const YAxis = createDynamicComponent(() =>
  import("recharts").then((mod) => mod.YAxis as any)
);

export const Tooltip = createDynamicComponent(() =>
  import("recharts").then((mod) => mod.Tooltip as any)
);

// Export types for better TypeScript support
export type ResponsiveContainerProps = ComponentProps<typeof ResponsiveContainer>;
export type AreaChartProps = ComponentProps<typeof AreaChart>;
export type LineChartProps = ComponentProps<typeof LineChart>;
export type AreaProps = ComponentProps<typeof Area>;
export type LineProps = ComponentProps<typeof Line>;
export type CartesianGridProps = ComponentProps<typeof CartesianGrid>;
export type XAxisProps = ComponentProps<typeof XAxis>;
export type YAxisProps = ComponentProps<typeof YAxis>;
export type TooltipProps = ComponentProps<typeof Tooltip>;
