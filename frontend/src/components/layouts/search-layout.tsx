"use client";

import { cn } from "@/lib/utils";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface SearchNavProps extends React.HTMLAttributes<HTMLElement> {
  items: {
    href: string;
    title: string;
    icon?: React.ReactNode;
  }[];
}

export function SearchNav({ className, items, ...props }: SearchNavProps) {
  const pathname = usePathname();

  return (
    <nav className={cn("flex space-x-2 lg:space-x-4", className)} {...props}>
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

export function SearchLayout({ children }: { children: React.ReactNode }) {
  const searchNavItems = [
    { href: "/dashboard/search", title: "All" },
    { href: "/dashboard/search/flights", title: "Flights" },
    { href: "/dashboard/search/hotels", title: "Hotels" },
    { href: "/dashboard/search/activities", title: "Activities" },
    { href: "/dashboard/search/destinations", title: "Destinations" },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="border-b pb-4">
        <h1 className="text-2xl font-semibold tracking-tight">Search</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Find flights, hotels, activities, and destinations for your next trip
        </p>
      </div>
      <div className="flex-1">
        <SearchNav items={searchNavItems} className="mb-8" />
        <div className="mt-4">{children}</div>
      </div>
    </div>
  );
}
