"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

interface SidebarNavProps extends React.HTMLAttributes<HTMLElement> {
  items: {
    href: string;
    title: string;
    icon?: React.ReactNode;
  }[];
}

export function SidebarNav({ className, items, ...props }: SidebarNavProps) {
  const pathname = usePathname();

  return (
    <nav
      className={cn(
        "flex space-x-2 lg:flex-col lg:space-x-0 lg:space-y-1",
        className
      )}
      {...props}
    >
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={cn(
            "flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
            pathname === item.href
              ? "bg-accent text-accent-foreground"
              : "transparent"
          )}
        >
          {item.icon && <span className="mr-2">{item.icon}</span>}
          {item.title}
        </Link>
      ))}
    </nav>
  );
}

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const navItems = [
    { href: "/dashboard", title: "Overview" },
    { href: "/dashboard/trips", title: "My Trips" },
    { href: "/dashboard/search", title: "Search" },
    { href: "/dashboard/chat", title: "AI Assistant" },
    { href: "/dashboard/agent-status", title: "Agent Status" },
    { href: "/dashboard/settings", title: "Settings" },
    { href: "/dashboard/profile", title: "Profile" },
  ];

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 flex h-16 items-center gap-4 border-b bg-background px-6">
        <Link
          href="/dashboard"
          className="flex items-center gap-2 font-semibold"
        >
          TripSage AI
        </Link>
        <div className="ml-auto flex items-center gap-4">
          <UserNav />
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

function UserNav() {
  return (
    <div className="flex items-center gap-2">
      <div className="rounded-full bg-primary h-8 w-8 flex items-center justify-center text-primary-foreground">
        U
      </div>
      <span className="text-sm font-medium">User</span>
    </div>
  );
}
