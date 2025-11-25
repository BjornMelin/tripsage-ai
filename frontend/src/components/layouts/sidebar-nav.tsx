/**
 * @fileoverview Sidebar navigation component.
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

/**
 * Props interface for the SidebarNav component.
 */
interface SidebarNavProps extends React.HTMLAttributes<HTMLElement> {
  /** Array of navigation items with href, title, and optional icon. */
  items: {
    href: string;
    title: string;
    icon?: React.ReactNode;
  }[];
}

/**
 * Navigation component for sidebar with active route highlighting.
 *
 * @param className - Additional CSS classes to apply.
 * @param items - Array of navigation items to display.
 * @param props - Additional HTML attributes.
 * @returns The SidebarNav component.
 */
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
            (
              item.href === "/dashboard"
                ? pathname === "/dashboard"
                : pathname?.startsWith(item.href)
            )
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
