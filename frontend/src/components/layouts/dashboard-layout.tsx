"use client";

import { ChevronDown, LogOut, Settings, User as UserIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useTransition } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ThemeToggle } from "@/components/ui/theme-toggle";
// import { logoutAction } from "@/lib/auth/server-actions"; // TODO: Replace with Supabase Auth
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
      className={cn("flex space-x-2 lg:flex-col lg:space-x-0 lg:space-y-1", className)}
      {...props}
    >
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={cn(
            "flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
            pathname === item.href ? "bg-accent text-accent-foreground" : "transparent"
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
        <Link href="/dashboard" className="flex items-center gap-2 font-semibold">
          TripSage AI
        </Link>
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
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
  const [isPending, startTransition] = useTransition();
  const [isOpen, setIsOpen] = useState(false);

  const handleLogout = () => {
    startTransition(async () => {
      setIsOpen(false);
      // TODO: Replace with Supabase Auth logout
      // await logoutAction();
      console.log("Logout functionality to be implemented with Supabase Auth");
    });
  };

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" className="flex items-center gap-2 px-3 py-2">
          <Avatar className="h-8 w-8">
            <AvatarFallback className="bg-primary text-primary-foreground">
              U
            </AvatarFallback>
          </Avatar>
          <span className="text-sm font-medium hidden sm:block">User</span>
          <ChevronDown className="h-4 w-4 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-56 p-0" align="end">
        <div className="space-y-1">
          <div className="px-3 py-2 border-b">
            <p className="text-sm font-medium">User</p>
            <p className="text-xs text-muted-foreground">user@example.com</p>
          </div>

          <div className="p-1">
            <Link
              href="/dashboard/profile"
              className="flex items-center gap-2 px-2 py-2 text-sm rounded-sm hover:bg-accent hover:text-accent-foreground transition-colors"
              onClick={() => setIsOpen(false)}
            >
              <UserIcon className="h-4 w-4" />
              Profile
            </Link>

            <Link
              href="/dashboard/settings"
              className="flex items-center gap-2 px-2 py-2 text-sm rounded-sm hover:bg-accent hover:text-accent-foreground transition-colors"
              onClick={() => setIsOpen(false)}
            >
              <Settings className="h-4 w-4" />
              Settings
            </Link>

            <div className="border-t my-1" />

            <button
              type="button"
              onClick={handleLogout}
              disabled={isPending}
              className="w-full flex items-center gap-2 px-2 py-2 text-sm rounded-sm hover:bg-accent hover:text-accent-foreground transition-colors disabled:opacity-50"
            >
              <LogOut className="h-4 w-4" />
              {isPending ? "Logging out..." : "Log out"}
            </button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
