"use client";

import dynamic from "next/dynamic";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import type { ComponentProps } from "react";

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

export const Area = dynamic(() => import("recharts").then((mod) => mod.Area), {
  ssr: false,
});

export const Line = dynamic(() => import("recharts").then((mod) => mod.Line), {
  ssr: false,
});

export const CartesianGrid = dynamic(
  () => import("recharts").then((mod) => mod.CartesianGrid),
  { ssr: false }
);

export const XAxis = dynamic(() => import("recharts").then((mod) => mod.XAxis), {
  ssr: false,
});

export const YAxis = dynamic(() => import("recharts").then((mod) => mod.YAxis), {
  ssr: false,
});

export const Tooltip = dynamic(() => import("recharts").then((mod) => mod.Tooltip), {
  ssr: false,
});

// Export types for better TypeScript support
export type ResponsiveContainerProps = ComponentProps<typeof ResponsiveContainer>;
export type AreaChartProps = ComponentProps<typeof AreaChart>;
export type LineChartProps = ComponentProps<typeof LineChart>;
