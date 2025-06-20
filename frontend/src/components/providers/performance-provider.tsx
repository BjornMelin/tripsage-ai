"use client";

import { useWebVitals } from "@/hooks/use-performance";
import type { ReactNode } from "react";

interface PerformanceMonitorProps {
  children: ReactNode;
}

export function PerformanceMonitor({ children }: PerformanceMonitorProps) {
  // Initialize Web Vitals monitoring
  useWebVitals();

  return <>{children}</>;
}
