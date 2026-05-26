"use client";

import { Toaster as SonnerToaster } from "sonner";
import { useTheme } from "@/hooks/use-theme";

/**
 * Toast notification container using Sonner.
 *
 * Integrates with the app theme provider for automatic light/dark theme support.
 * Renders at bottom-right on desktop, top on mobile.
 */
export function Toaster() {
  const { theme = "system" } = useTheme();

  return (
    <SonnerToaster
      theme={theme as "light" | "dark" | "system"}
      className="toaster group"
      toastOptions={{
        classNames: {
          actionButton:
            "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton: "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
          description: "group-[.toast]:text-muted-foreground",
          toast:
            "group toast group-[.toaster]:bg-background group-[.toaster]:text-foreground group-[.toaster]:border-border group-[.toaster]:shadow-lg",
        },
      }}
    />
  );
}
