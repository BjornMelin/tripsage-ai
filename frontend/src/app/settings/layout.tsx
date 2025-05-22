"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navItems = [
  { name: "API Keys", href: "/settings/api-keys" },
  // Add more settings sections as needed
];

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="container grid md:grid-cols-[240px_1fr] gap-8 py-8">
      <aside className="flex flex-col gap-2">
        <nav className="flex flex-col gap-2">
          <h3 className="text-lg font-medium mb-2">Settings</h3>
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "p-2 rounded-md hover:bg-muted transition-colors",
                pathname === item.href && "bg-muted font-medium"
              )}
            >
              {item.name}
            </Link>
          ))}
        </nav>
      </aside>
      <main>{children}</main>
    </div>
  );
}
