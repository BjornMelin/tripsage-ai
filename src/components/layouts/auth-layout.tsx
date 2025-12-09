"use client";

import Link from "next/link";

export function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex h-16 items-center gap-4 border-b bg-background px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          TripSage AI
        </Link>
      </header>
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md space-y-6">{children}</div>
      </main>
      <footer className="border-t py-4 px-6 text-center text-sm text-muted-foreground">
        <p>© {new Date().getFullYear()} TripSage AI. All rights reserved.</p>
      </footer>
    </div>
  );
}
