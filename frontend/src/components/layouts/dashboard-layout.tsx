/**
 * @fileoverview DashboardLayout components providing the main application layout
 * with sidebar navigation, header, and user account management for the dashboard
 * experience.
 */

import { ThemeToggle } from "@/components/ui/theme-toggle";
import { mapSupabaseUserToAuthUser, requireUser } from "@/lib/auth/server";
import Link from "next/link";
import { SidebarNav } from "./sidebar-nav";
import { UserNav } from "./user-nav";

/**
 * Main dashboard layout component with sidebar navigation and header.
 *
 * Provides the overall structure for dashboard pages with navigation sidebar,
 * header with user controls, and main content area.
 *
 * @param children - Content to render in the main area.
 * @returns The DashboardLayout component.
 */
export async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user: supabaseUser } = await requireUser();
  const user = mapSupabaseUserToAuthUser(supabaseUser);

  const navItems = [
    { href: "/dashboard", title: "Overview" },
    { href: "/dashboard/trips", title: "My Trips" },
    { href: "/dashboard/search", title: "Search" },
    { href: "/dashboard/calendar", title: "Calendar" },
    { href: "/chat", title: "AI Assistant" },
    { href: "/dashboard/agent-status", title: "Agent Status" },
    { href: "/dashboard/settings", title: "Settings" },
    { href: "/dashboard/profile", title: "Profile" },
  ];

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 flex h-16 items-center gap-4 border-b bg-background px-6">
        <Link href="/dashboard" className="flex items-center gap-2 font-semibold">
          TripSage AI
        </Link>
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          <UserNav user={user} />
        </div>
      </header>
      <div className="flex-1 grid grid-cols-[220px_1fr]">
        <aside className="border-r bg-background h-full">
          <div className="flex flex-col gap-4 p-4">
            <SidebarNav items={navItems} />
          </div>
        </aside>
        <main className="flex-1 p-6 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
