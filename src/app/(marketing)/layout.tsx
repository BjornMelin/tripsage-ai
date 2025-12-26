/**
 * @fileoverview Marketing/public pages layout with navigation.
 */

import { type ReactNode, Suspense } from "react";
import { Navbar } from "@/components/layouts/navbar";
import { Skeleton } from "@/components/ui/skeleton";

function NavbarFallback() {
  return (
    <header className="border-b bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60">
      <nav
        className="container flex h-16 items-center justify-between"
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
