"use client";

import type { ReactNode } from "react";
import { useWebVitals } from "@/hooks/use-performance";

interface PerformanceMonitorProps {
  children: ReactNode;
}

export function PerformanceMonitor({ children }: PerformanceMonitorProps) {
  // Initialize Web Vitals monitoring
  useWebVitals();

  return <>{children}</>;
}
