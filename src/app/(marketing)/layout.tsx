/**
 * @fileoverview Marketing/public pages layout with navigation.
 */

import { type ReactNode, Suspense } from "react";
import { Navbar } from "@/components/layouts/navbar";
import { Skeleton } from "@/components/ui/skeleton";

function NavbarFallback() {
  return (
    <header className="sticky top-0 z-50 border-b bg-background/90 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <nav
        className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8"
        aria-busy="true"
        aria-label="Loading navigation"
      >
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2" aria-hidden="true">
            <Skeleton className="h-8 w-8 rounded-md" />
            <Skeleton className="h-6 w-20 rounded-md" />
          </div>
          <div className="hidden md:flex items-center gap-6" aria-hidden="true">
            <Skeleton className="h-4 w-12 rounded-full" />
            <Skeleton className="h-4 w-14 rounded-full" />
            <Skeleton className="h-4 w-16 rounded-full" />
          </div>
        </div>
        <div className="flex items-center gap-2" aria-hidden="true">
          <Skeleton className="h-8 w-8 rounded-full" />
          <Skeleton className="h-8 w-16 rounded-md" />
          <Skeleton className="h-8 w-20 rounded-md" />
          <Skeleton className="h-9 w-9 rounded-md md:hidden" />
        </div>
      </nav>
    </header>
  );
}

/**
 * Marketing route-group layout that renders the public Navbar (via Suspense) and page content.
 *
 * Uses a skeleton fallback to preserve navbar layout while the Navbar loads.
 *
 * @param children - React content to render as the layout body.
 */
export default function MarketingLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <Suspense fallback={<NavbarFallback />}>
        <Navbar />
      </Suspense>
      {children}
    </>
  );
}
