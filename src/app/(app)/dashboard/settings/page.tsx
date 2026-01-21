/**
 * @fileoverview Dashboard settings landing page.
 */

"use client";

import { ArrowRightIcon } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ROUTES } from "@/lib/routes";

export default function DashboardSettingsPage() {
  return (
    <section aria-labelledby="dashboard-settings-title">
      <h1 id="dashboard-settings-title" className="mb-8 text-3xl font-bold">
        Settings
      </h1>

      <div className="grid gap-6">
        <Card className="group transition-shadow hover:shadow-md">
          <CardHeader>
            <CardTitle id="settings-api-keys-title">API Key Management</CardTitle>
            <CardDescription id="settings-api-keys-description">
              Manage your API keys for external services
            </CardDescription>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Add, validate, and remove API keys for services like maps, weather, and
              more.
            </p>
            <ArrowRightIcon className="h-5 w-5 text-muted-foreground transition-transform group-hover:translate-x-1" />
          </CardContent>
          <CardFooter className="justify-end">
            <Button asChild>
              <Link
                href={ROUTES.dashboard.settingsApiKeys}
                aria-labelledby="settings-api-keys-title"
                aria-describedby="settings-api-keys-description"
              >
                Manage API keys
              </Link>
            </Button>
          </CardFooter>
        </Card>
      </div>
    </section>
  );
}
