/**
 * @fileoverview Filter presets component for saving and loading filter configurations.
 */

"use client";

import type { FilterPreset } from "@schemas/stores";
import { BookmarkIcon, CheckIcon, PencilIcon, PlusIcon, TrashIcon } from "lucide-react";
import { useState } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useSearchFiltersStore } from "@/stores/search-filters-store";

/** Props for the filter presets component */
interface FilterPresetsProps {
  className?: string;
}

/** Filter presets component for saving and loading filter configurations. */
export function FilterPresets({ className }: FilterPresetsProps) {
  const [newPresetName, setNewPresetName] = useState("");
  const [newPresetDescription, setNewPresetDescription] = useState("");
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [editingPreset, setEditingPreset] = useState<FilterPreset | null>(null);

  const {
    filterPresets,
    activePreset,
    hasActiveFilters,
    currentSearchType,
    saveFilterPreset,
    loadFilterPreset,
    deleteFilterPreset,
    updateFilterPreset,
    duplicateFilterPreset,
  } = useSearchFiltersStore();

  const effectiveSearchType = currentSearchType ?? "flight";

  // Filter presets for current search type
  const currentPresets = filterPresets.filter(
    (preset) => preset.searchType === effectiveSearchType
  );

  /** Save a new filter preset */
  const handleSavePreset = () => {
    if (!newPresetName.trim()) return;

    const presetId = saveFilterPreset(
      newPresetName.trim(),
      newPresetDescription.trim() || undefined
    );
    if (presetId) {
      setNewPresetName("");
      setNewPresetDescription("");
      setIsCreateDialogOpen(false);
    }
  };

  /** Load a filter preset */
  const handleLoadPreset = (presetId: string) => {
    loadFilterPreset(presetId);
  };

  /** Delete a filter preset */
  const handleDeletePreset = (presetId: string) => {
    deleteFilterPreset(presetId);
  };

  /** Update a filter preset */
  const handleUpdatePreset = () => {
    if (!editingPreset || !newPresetName.trim()) return;

    updateFilterPreset(editingPreset.id, {
      description: newPresetDescription.trim() || undefined,
      name: newPresetName.trim(),
    });
    setEditingPreset(null);
    setNewPresetName("");
    setNewPresetDescription("");
  };

  /** Duplicate a filter preset */
  const handleDuplicatePreset = (presetId: string, originalName: string) => {
    duplicateFilterPreset(presetId, `${originalName} (Copy)`);
  };

  /** Start editing a filter preset */
  const startEditing = (preset: FilterPreset) => {
    setEditingPreset(preset);
    setNewPresetName(preset.name);
    setNewPresetDescription(preset.description || "");
  };

  return (
    <Card className={className} data-testid="filter-presets">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <BookmarkIcon className="h-4 w-4" />
              Filter Presets
            </CardTitle>
            <CardDescription className="text-xs mt-1">
              Save and reuse your filter combinations
            </CardDescription>
          </div>
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                disabled={!hasActiveFilters}
                title={
                  hasActiveFilters
                    ? "Save current filters as preset"
                    : "Apply some filters first"
                }
              >
                <PlusIcon className="h-4 w-4 mr-1" />
                Save
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Save Filter Preset</DialogTitle>
                <DialogDescription>
                  Save your current filter configuration for quick access later.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="preset-name">Name</Label>
                  <Input
                    id="preset-name"
                    placeholder="e.g., Budget European Flights"
                    value={newPresetName}
                    onChange={(e) => setNewPresetName(e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="preset-description">Description (optional)</Label>
                  <Input
                    id="preset-description"
                    placeholder="e.g., Direct flights under $500"
                    value={newPresetDescription}
                    onChange={(e) => setNewPresetDescription(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleSavePreset} disabled={!newPresetName.trim()}>
                  Save Preset
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </CardHeader>
      <CardContent>
        {currentPresets.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No presets saved yet. Apply filters and save them for quick access.
          </p>
        ) : (
          <div className="space-y-2">
            {currentPresets.map((preset) => (
              <div
                key={preset.id}
                className={`flex items-center justify-between p-2 rounded-md border ${
                  activePreset?.id === preset.id
                    ? "border-primary bg-primary/5"
                    : "border-border hover:bg-accent/50"
                }`}
              >
                <button
                  type="button"
                  className="flex-1 text-left"
                  onClick={() => handleLoadPreset(preset.id)}
                >
                  <div className="flex items-center gap-2">
                    {activePreset?.id === preset.id && (
                      <CheckIcon className="h-3 w-3 text-primary" />
                    )}
                    <span className="text-sm font-medium">{preset.name}</span>
                    {preset.isBuiltIn && (
                      <span className="text-xs bg-muted px-1 rounded">Built-in</span>
                    )}
                  </div>
                  {preset.description && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {preset.description}
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {preset.filters.length} filter
                    {preset.filters.length !== 1 ? "s" : ""} • Used {preset.usageCount}{" "}
                    time{preset.usageCount !== 1 ? "s" : ""}
                  </p>
                </button>

                {!preset.isBuiltIn && (
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                        <span className="sr-only">Open menu</span>
                        <PencilIcon className="h-3 w-3" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-40 p-1" align="end">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full justify-start"
                        onClick={() => startEditing(preset)}
                      >
                        <PencilIcon className="h-3 w-3 mr-2" />
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full justify-start"
                        onClick={() => handleDuplicatePreset(preset.id, preset.name)}
                      >
                        <PlusIcon className="h-3 w-3 mr-2" />
                        Duplicate
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="w-full justify-start text-destructive hover:text-destructive"
                          >
                            <TrashIcon className="h-3 w-3 mr-2" />
                            Delete
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete Preset</AlertDialogTitle>
                            <AlertDialogDescription>
                              Are you sure you want to delete &quot;{preset.name}&quot;?
                              This action cannot be undone.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              onClick={() => handleDeletePreset(preset.id)}
                            >
                              Delete
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </PopoverContent>
                  </Popover>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Edit Dialog */}
        <Dialog
          open={editingPreset !== null}
          onOpenChange={(open) => !open && setEditingPreset(null)}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit Preset</DialogTitle>
              <DialogDescription>
                Update the name or description of this preset.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="edit-preset-name">Name</Label>
                <Input
                  id="edit-preset-name"
                  value={newPresetName}
                  onChange={(e) => setNewPresetName(e.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="edit-preset-description">Description (optional)</Label>
                <Input
                  id="edit-preset-description"
                  value={newPresetDescription}
                  onChange={(e) => setNewPresetDescription(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditingPreset(null)}>
                Cancel
              </Button>
              <Button onClick={handleUpdatePreset} disabled={!newPresetName.trim()}>
                Save Changes
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
