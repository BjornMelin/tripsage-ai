/**
 * @fileoverview User navigation component.
 */

"use client";

import { ChevronDown, LogOut, Settings, User as UserIcon } from "lucide-react";
import Link from "next/link";
import { useState, useTransition } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import type { AuthUser } from "@/domain/schemas/stores";
import { logoutAction } from "@/lib/auth/actions";

interface UserNavProps {
  user: AuthUser;
}

/**
 * User navigation component with profile dropdown and logout functionality.
 *
 * Displays user avatar and provides access to profile, settings, and logout
 * options via a popover menu.
 *
 * @param user - The authenticated user.
 * @returns The UserNav component.
 */
export function UserNav({ user }: UserNavProps) {
  const [isPending, startTransition] = useTransition();
  const [isOpen, setIsOpen] = useState(false);

  const handleLogout = () => {
    startTransition(async () => {
      setIsOpen(false);
      await logoutAction();
    });
  };

  // Get initials for avatar fallback
  const initials = user.displayName
    ? user.displayName
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : user.email?.slice(0, 2).toUpperCase() || "U";

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" className="flex items-center gap-2 px-3 py-2">
          <Avatar className="h-8 w-8">
            <AvatarImage src={user.avatarUrl} alt={user.displayName || "User"} />
            <AvatarFallback className="bg-primary text-primary-foreground">
              {initials}
            </AvatarFallback>
          </Avatar>
          <span className="text-sm font-medium hidden sm:block">
            {user.displayName || user.email || "User"}
          </span>
          <ChevronDown className="h-4 w-4 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-56 p-0" align="end">
        <div className="space-y-1">
          <div className="px-3 py-2 border-b">
            <p className="text-sm font-medium">{user.displayName || "User"}</p>
            <p className="text-xs text-muted-foreground">{user.email}</p>
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
