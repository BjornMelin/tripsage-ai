"use client";

import { useEffect, useState } from "react";

interface PerformanceMetrics {
  loadTime: number;
  renderTime: number;
  bundleSize: number;
  isHydrated: boolean;
}

export function usePerformance() {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    loadTime: 0,
    renderTime: 0,
    bundleSize: 0,
    isHydrated: false,
  });

  useEffect(() => {
    // Check if performance API is available
    if (typeof window === "undefined" || !window.performance) return;

    const startTime = performance.now();

    // Measure initial load time
    const loadTime =
      performance.timing?.loadEventEnd - performance.timing?.navigationStart || 0;

    // Measure render time
    const renderTime = performance.now() - startTime;

    // Estimate bundle size from network requests
    let bundleSize = 0;
    if (performance.getEntriesByType) {
      const resourceEntries = performance.getEntriesByType(
        "resource"
      ) as PerformanceResourceTiming[];
      bundleSize = resourceEntries
        .filter((entry) => entry.name.includes(".js") || entry.name.includes(".css"))
        .reduce((total, entry) => total + (entry.transferSize || 0), 0);
    }

    setMetrics({
      loadTime,
      renderTime,
      bundleSize,
      isHydrated: true,
    });

    // Report to console in development
    if (process.env.NODE_ENV === "development") {
      console.log("Performance Metrics:", {
        loadTime: `${loadTime}ms`,
        renderTime: `${renderTime.toFixed(2)}ms`,
        bundleSize: `${(bundleSize / 1024).toFixed(2)}KB`,
      });
    }
  }, []);

  return metrics;
}

// Hook to measure component render time
export function useComponentPerformance(componentName: string) {
  useEffect(() => {
    if (process.env.NODE_ENV !== "development") return;

    const startTime = performance.now();

    return () => {
      const renderTime = performance.now() - startTime;
      console.log(`Component ${componentName} render time: ${renderTime.toFixed(2)}ms`);
    };
  }, [componentName]);
}

// Hook to report Web Vitals
export function useWebVitals() {
  useEffect(() => {
    if (typeof window === "undefined") return;

    // Dynamically import web-vitals to avoid increasing bundle size
    import("web-vitals")
      .then(({ onCLS, onINP, onFCP, onLCP, onTTFB }) => {
        onCLS(console.log);
        onINP(console.log); // Replaced getFID with onINP in v5
        onFCP(console.log);
        onLCP(console.log);
        onTTFB(console.log);
      })
      .catch(() => {
        // Silently fail if web-vitals is not available
      });
  }, []);
}
