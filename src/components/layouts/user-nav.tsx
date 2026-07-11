/**
 * @fileoverview User navigation component.
 */

"use client";

import type { AuthUser } from "@schemas/stores";
import {
  ChevronDownIcon,
  LogOutIcon,
  SettingsIcon,
  ShieldIcon,
  UserIcon,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useTransition } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useToast } from "@/components/ui/use-toast";
import { useAuthCore } from "@/features/auth/store/auth/auth-core";
import { ROUTES } from "@/lib/routes";

interface UserNavProps {
  user: AuthUser;
}

/**
 * User navigation component with profile dropdown and logout functionality.
 *
 * Displays user avatar and provides access to profile, settings, and logout
 * options via a dropdown menu.
 *
 * @param user - The authenticated user.
 * @returns The UserNav component.
 */
export function UserNav({ user }: UserNavProps) {
  const router = useRouter();
  const { toast } = useToast();
  const logout = useAuthCore((state) => state.logout);
  const [isPending, startTransition] = useTransition();

  const handleLogout = useCallback(() => {
    startTransition(async () => {
      try {
        await logout();
        router.replace(ROUTES.login);
        router.refresh();
      } catch {
        toast({
          description: "Your session is still active. Please try again.",
          title: "Logout failed",
          variant: "destructive",
        });
      }
    });
  }, [logout, router, toast]);

  // Get initials for avatar fallback
  const initials = user.displayName
    ? user.displayName
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : user.email?.slice(0, 2).toUpperCase() || "U";
  const userLabel = user.displayName || user.email || "user";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="flex items-center gap-2 px-3 py-2"
          aria-label={`Open account menu for ${userLabel}`}
        >
          <Avatar className="h-8 w-8">
            <AvatarImage src={user.avatarUrl} alt={user.displayName || "User"} />
            <AvatarFallback className="bg-primary text-primary-foreground">
              {initials}
            </AvatarFallback>
          </Avatar>
          <span className="text-sm font-medium hidden sm:block">
            {user.displayName || user.email || "User"}
          </span>
          <ChevronDownIcon aria-hidden="true" className="h-4 w-4 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="px-3 py-2">
          <p className="text-sm font-medium">{user.displayName || "User"}</p>
          <p className="text-xs text-muted-foreground">{user.email}</p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href={ROUTES.dashboard.profile}>
            <UserIcon aria-hidden="true" className="h-4 w-4" />
            Profile
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href={ROUTES.dashboard.settings}>
            <SettingsIcon aria-hidden="true" className="h-4 w-4" />
            Settings
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href={ROUTES.dashboard.security}>
            <ShieldIcon aria-hidden="true" className="h-4 w-4" />
            Security
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={handleLogout} disabled={isPending}>
          <LogOutIcon aria-hidden="true" className="h-4 w-4" />
          {isPending ? "Logging Out…" : "Log Out"}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
