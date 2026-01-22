/**
 * @fileoverview Trip settings form panel for editing trip metadata.
 */

"use client";

import type { TripSettingsFormData } from "@schemas/trips";
import { Loader2Icon } from "lucide-react";
import type { Dispatch, SetStateAction } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";

type TripSettingsPanelProps = {
  settings: TripSettingsFormData;
  setSettings: Dispatch<SetStateAction<TripSettingsFormData>>;
  isSaving: boolean;
  onReset: () => void;
  onSave: () => void;
};

export function TripSettingsPanel({
  settings,
  setSettings,
  isSaving,
  onReset,
  onSave,
}: TripSettingsPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Trip settings</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="trip-title">Title</Label>
            <Input
              id="trip-title"
              value={settings.title}
              onChange={(e) =>
                setSettings((prev) => ({ ...prev, title: e.target.value }))
              }
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="trip-destination">Destination</Label>
            <Input
              id="trip-destination"
              value={settings.destination ?? ""}
              onChange={(e) => {
                const nextValue = e.target.value;
                setSettings((prev) => ({
                  ...prev,
                  destination: nextValue.length ? nextValue : undefined,
                }));
              }}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="trip-start-date">Start date</Label>
            <Input
              id="trip-start-date"
              type="date"
              value={settings.startDate ?? ""}
              onChange={(e) => {
                const nextValue = e.target.value;
                setSettings((prev) => ({
                  ...prev,
                  startDate: nextValue ? nextValue : undefined,
                }));
              }}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="trip-end-date">End date</Label>
            <Input
              id="trip-end-date"
              type="date"
              value={settings.endDate ?? ""}
              onChange={(e) => {
                const nextValue = e.target.value;
                setSettings((prev) => ({
                  ...prev,
                  endDate: nextValue ? nextValue : undefined,
                }));
              }}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="trip-description">Description</Label>
          <Textarea
            id="trip-description"
            value={settings.description ?? ""}
            onChange={(e) => {
              const nextValue = e.target.value;
              setSettings((prev) => ({
                ...prev,
                description: nextValue,
              }));
            }}
            rows={4}
          />
        </div>

        <Separator />

        <div className="flex flex-wrap items-center justify-end gap-2">
          <Button type="button" variant="outline" onClick={onReset}>
            Reset
          </Button>
          <Button type="button" onClick={onSave} disabled={isSaving}>
            {isSaving ? (
              <Loader2Icon aria-hidden="true" className="mr-2 h-4 w-4 animate-spin" />
            ) : null}
            Save changes
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
