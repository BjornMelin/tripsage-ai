/**
 * @fileoverview Chart wrapper component for dynamically importing Recharts components to reduce initial bundle size.
 */

"use client";

import dynamic from "next/dynamic";
import type { ComponentProps, ComponentType } from "react";
import type {
  AreaProps as RechartsAreaProps,
  LineProps as RechartsLineProps,
  TooltipProps as RechartsTooltipProps,
  XAxisProps as RechartsXAxisProps,
  YAxisProps as RechartsYAxisProps,
} from "recharts";
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

/**
 * Dynamically import the AreaChart component.
 *
 * @returns The AreaChart component.
 */
export const AreaChart = dynamic(
  () => import("recharts").then((mod) => mod.AreaChart),
  { ssr: false }
);

/**
 * Dynamically import the LineChart component.
 *
 * @returns The LineChart component.
 */
export const LineChart = dynamic(
  () => import("recharts").then((mod) => mod.LineChart),
  { ssr: false }
);

/**
 * Dynamically import the Area component.
 *
 * @returns The Area component.
 */
export const Area = CreateDynamicComponent(() =>
  import("recharts").then(
    (mod) => mod.Area as unknown as React.ComponentType<RechartsAreaProps>
  )
);

/**
 * Dynamically import the Line component.
 *
 * @returns The Line component.
 */
export const Line = CreateDynamicComponent(() =>
  import("recharts").then(
    (mod) => mod.Line as unknown as React.ComponentType<RechartsLineProps>
  )
);

/**
 * Dynamically import the CartesianGrid component.
 *
 * @returns The CartesianGrid component.
 */
export const CartesianGrid = dynamic(
  () => import("recharts").then((mod) => mod.CartesianGrid),
  { ssr: false }
);

/**
 * Dynamically import the XAxis component.
 *
 * @returns The XAxis component.
 */
export const XAxis = CreateDynamicComponent(() =>
  import("recharts").then(
    (mod) => mod.XAxis as unknown as React.ComponentType<RechartsXAxisProps>
  )
);

/**
 * Dynamically import the YAxis component.
 *
 * @returns The YAxis component.
 */
export const YAxis = CreateDynamicComponent(() =>
  import("recharts").then(
    (mod) => mod.YAxis as unknown as React.ComponentType<RechartsYAxisProps>
  )
);

/**
 * Dynamically import the Tooltip component.
 *
 * @returns The Tooltip component.
 */
export const Tooltip = CreateDynamicComponent(() =>
  import("recharts").then(
    (mod) =>
      mod.Tooltip as unknown as React.ComponentType<RechartsTooltipProps<any, any>>
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
