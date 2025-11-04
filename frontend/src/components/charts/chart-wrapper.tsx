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

/** Use the safe dynamic wrapper for problematic components */
export const Area = CreateDynamicComponent(() =>
  import("recharts").then(
    (mod) => mod.Area as unknown as React.ComponentType<Record<string, unknown>>
  )
);

export const Line = CreateDynamicComponent(() =>
  import("recharts").then(
    (mod) => mod.Line as unknown as React.ComponentType<Record<string, unknown>>
  )
);

export const CartesianGrid = dynamic(
  () => import("recharts").then((mod) => mod.CartesianGrid),
  { ssr: false }
);

export const XAxis = CreateDynamicComponent(() =>
  import("recharts").then(
    (mod) => mod.XAxis as unknown as React.ComponentType<Record<string, unknown>>
  )
);

export const YAxis = CreateDynamicComponent(() =>
  import("recharts").then(
    (mod) => mod.YAxis as unknown as React.ComponentType<Record<string, unknown>>
  )
);

export const Tooltip = CreateDynamicComponent(() =>
  import("recharts").then(
    (mod) => mod.Tooltip as unknown as React.ComponentType<Record<string, unknown>>
  )
);

/** Export types for better TypeScript support */
export type ResponsiveContainerProps = ComponentProps<typeof ResponsiveContainer>;
export type AreaChartProps = ComponentProps<typeof AreaChart>;
export type LineChartProps = ComponentProps<typeof LineChart>;
export type AreaProps = ComponentProps<typeof Area>;
export type LineProps = ComponentProps<typeof Line>;
export type CartesianGridProps = ComponentProps<typeof CartesianGrid>;
export type XAxisProps = ComponentProps<typeof XAxis>;
export type YAxisProps = ComponentProps<typeof YAxis>;
export type TooltipProps = ComponentProps<typeof Tooltip>;
