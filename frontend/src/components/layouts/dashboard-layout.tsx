/**
 * @fileoverview DashboardLayout components providing the main application layout
 * with sidebar navigation, header, and user account management for the dashboard
 * experience.
 */

import type { AuthUser } from "@schemas/stores";
import Link from "next/link";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { mapSupabaseUserToAuthUser, requireUser } from "@/lib/auth/server";
import { SidebarNav } from "./sidebar-nav";
import { UserNav } from "./user-nav";

/** Dashboard navigation link metadata used by the layout. */
export interface DashboardNavItem {
  href: string;
  title: string;
  icon?: React.ReactNode;
}

export interface DashboardLayoutData {
  navItems: ReadonlyArray<DashboardNavItem>;
  user: AuthUser;
}

export const DASHBOARD_NAV_ITEMS: ReadonlyArray<DashboardNavItem> = [
  { href: "/dashboard", title: "Overview" },
  { href: "/dashboard/trips", title: "My Trips" },
  { href: "/dashboard/search", title: "Search" },
  { href: "/dashboard/calendar", title: "Calendar" },
  // Chat is intentionally outside the dashboard namespace; keep `/chat` public.
  { href: "/chat", title: "AI Assistant" },
  { href: "/dashboard/agent-status", title: "Agent Status" },
  // Security is mounted at /security (top-level dashboard group)
  { href: "/security", title: "Security" },
  { href: "/dashboard/settings", title: "Settings" },
  { href: "/dashboard/profile", title: "Profile" },
];

/**
 * Fetches authenticated user and navigation data required by the dashboard layout.
 *
 * Isolated from the Server Component to enable focused unit tests without RSC rendering.
 */
// biome-ignore lint/style/useNamingConvention: helper function is not a React component
export async function fetchDashboardLayoutData(): Promise<DashboardLayoutData> {
  const { user: supabaseUser } = await requireUser();
  const user = mapSupabaseUserToAuthUser(supabaseUser);

  return { navItems: DASHBOARD_NAV_ITEMS, user };
}

interface DashboardLayoutViewProps {
  children: React.ReactNode;
  navItems?: ReadonlyArray<DashboardNavItem>;
  user: AuthUser;
}

/**
 * Pure presentational layout for the dashboard shell; expects resolved data.
 */
export function DashboardLayoutView({
  children,
  navItems = DASHBOARD_NAV_ITEMS,
  user,
}: DashboardLayoutViewProps) {
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

/**
 * Server Component wrapper that resolves auth/navigation data then renders the
 * presentational dashboard shell.
 *
 * @param children - Content to render in the main content area.
 */
export async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { navItems, user } = await fetchDashboardLayoutData();

  return (
    <DashboardLayoutView navItems={navItems} user={user}>
      {children}
    </DashboardLayoutView>
  );
}
