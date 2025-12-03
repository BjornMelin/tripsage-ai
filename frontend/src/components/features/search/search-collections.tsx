/**
 * @fileoverview Search collections component for organizing saved searches into groups.
 */

"use client";

import type { SearchCollection, ValidatedSavedSearch } from "@schemas/stores";
import {
  FolderIcon,
  FolderPlusIcon,
  MoreHorizontalIcon,
  PencilIcon,
  PlusIcon,
  TrashIcon,
} from "lucide-react";
import { useState } from "react";
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  useSearchCollections,
  useSearchHistoryStore,
} from "@/stores/search-history-store";

/** Props for the search collections component */
interface SearchCollectionsProps {
  className?: string;
  onSelectSearch?: (search: ValidatedSavedSearch) => void;
}

/** Search collections component for organizing saved searches into groups. */
export function SearchCollections({
  className,
  onSelectSearch,
}: SearchCollectionsProps) {
  const [newCollectionName, setNewCollectionName] = useState("");
  const [newCollectionDescription, setNewCollectionDescription] = useState("");
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [editingCollection, setEditingCollection] = useState<SearchCollection | null>(
    null
  );
  const [expandedCollection, setExpandedCollection] = useState<string | null>(null);

  const collections = useSearchCollections();
  const {
    savedSearches,
    createCollection,
    updateCollection,
    deleteCollection,
    removeSearchFromCollection,
  } = useSearchHistoryStore();

  /** Get saved searches for a collection */
  const getCollectionSearches = (collection: SearchCollection) => {
    return savedSearches.filter((search) => collection.searchIds.includes(search.id));
  };

  /** Handle create collection */
  const handleCreateCollection = async () => {
    if (!newCollectionName.trim()) return;

    const collectionId = await createCollection(
      newCollectionName.trim(),
      newCollectionDescription.trim() || undefined
    );
    if (collectionId) {
      setNewCollectionName("");
      setNewCollectionDescription("");
      setIsCreateDialogOpen(false);
    }
  };

  /** Handle update collection */
  const handleUpdateCollection = async () => {
    if (!editingCollection || !newCollectionName.trim()) return;

    await updateCollection(editingCollection.id, {
      description: newCollectionDescription.trim() || undefined,
      name: newCollectionName.trim(),
    });
    setEditingCollection(null);
    setNewCollectionName("");
    setNewCollectionDescription("");
  };

  /** Handle delete collection */
  const handleDeleteCollection = async (collectionId: string) => {
    await deleteCollection(collectionId);
    if (expandedCollection === collectionId) {
      setExpandedCollection(null);
    }
  };

  /** Handle remove from collection */
  const handleRemoveFromCollection = (collectionId: string, searchId: string) => {
    removeSearchFromCollection(collectionId, searchId);
  };

  /** Handle start editing */
  const startEditing = (collection: SearchCollection) => {
    setEditingCollection(collection);
    setNewCollectionName(collection.name);
    setNewCollectionDescription(collection.description || "");
  };

  /** Toggle expand */
  const toggleExpand = (collectionId: string) => {
    setExpandedCollection(expandedCollection === collectionId ? null : collectionId);
  };

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <FolderIcon className="h-4 w-4" />
              Collections
            </CardTitle>
            <CardDescription className="text-xs mt-1">
              Organize your saved searches into groups
            </CardDescription>
          </div>
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm">
                <FolderPlusIcon className="h-4 w-4 mr-1" />
                New
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create Collection</DialogTitle>
                <DialogDescription>
                  Create a new collection to organize your saved searches.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="collection-name">Name</Label>
                  <Input
                    id="collection-name"
                    placeholder="e.g., Summer 2025 Trip"
                    value={newCollectionName}
                    onChange={(e) => setNewCollectionName(e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="collection-description">Description (optional)</Label>
                  <Textarea
                    id="collection-description"
                    placeholder="e.g., Planning options for our family vacation"
                    value={newCollectionDescription}
                    onChange={(e) => setNewCollectionDescription(e.target.value)}
                    rows={2}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                  Cancel
                </Button>
                <Button
                  onClick={handleCreateCollection}
                  disabled={!newCollectionName.trim()}
                >
                  Create Collection
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </CardHeader>
      <CardContent>
        {collections.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No collections yet. Create one to organize your saved searches.
          </p>
        ) : (
          <div className="space-y-2">
            {collections.map((collection) => {
              const collectionSearches = getCollectionSearches(collection);
              const isExpanded = expandedCollection === collection.id;

              return (
                <div key={collection.id} className="border rounded-lg overflow-hidden">
                  <button
                    type="button"
                    className="w-full flex items-center justify-between p-3 hover:bg-accent/50 text-left"
                    onClick={() => toggleExpand(collection.id)}
                  >
                    <div className="flex items-center gap-2">
                      <FolderIcon
                        className={`h-4 w-4 ${isExpanded ? "text-primary" : "text-muted-foreground"}`}
                      />
                      <div>
                        <span className="text-sm font-medium">{collection.name}</span>
                        <span className="text-xs text-muted-foreground ml-2">
                          ({collectionSearches.length})
                        </span>
                      </div>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MoreHorizontalIcon className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => startEditing(collection)}>
                          <PencilIcon className="h-4 w-4 mr-2" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={() => handleDeleteCollection(collection.id)}
                        >
                          <TrashIcon className="h-4 w-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </button>

                  {isExpanded && (
                    <div className="border-t bg-muted/20 p-2">
                      {collection.description && (
                        <p className="text-xs text-muted-foreground mb-2 px-1">
                          {collection.description}
                        </p>
                      )}
                      {collectionSearches.length === 0 ? (
                        <p className="text-xs text-muted-foreground text-center py-2">
                          No searches in this collection
                        </p>
                      ) : (
                        <div className="space-y-1">
                          {collectionSearches.map((search) => (
                            <div
                              key={search.id}
                              className="flex items-center justify-between p-2 rounded hover:bg-accent/50"
                            >
                              <button
                                type="button"
                                className="flex-1 text-left"
                                onClick={() => onSelectSearch?.(search)}
                              >
                                <span className="text-sm">{search.name}</span>
                                <span className="text-xs text-muted-foreground ml-2 capitalize">
                                  {search.searchType}
                                </span>
                              </button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
                                onClick={() =>
                                  handleRemoveFromCollection(collection.id, search.id)
                                }
                                title="Remove from collection"
                              >
                                <TrashIcon className="h-3 w-3" />
                              </Button>
                            </div>
                          ))}
                        </div>
                      )}
                      {collection.tags.length > 0 && (
                        <div className="flex gap-1 mt-2 px-1">
                          {collection.tags.map((tag) => (
                            <span
                              key={tag}
                              className="text-xs bg-muted px-1.5 py-0.5 rounded"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Edit Dialog */}
        <Dialog
          open={editingCollection !== null}
          onOpenChange={(open) => !open && setEditingCollection(null)}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit Collection</DialogTitle>
              <DialogDescription>
                Update the collection name or description.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="edit-collection-name">Name</Label>
                <Input
                  id="edit-collection-name"
                  value={newCollectionName}
                  onChange={(e) => setNewCollectionName(e.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="edit-collection-description">
                  Description (optional)
                </Label>
                <Textarea
                  id="edit-collection-description"
                  value={newCollectionDescription}
                  onChange={(e) => setNewCollectionDescription(e.target.value)}
                  rows={2}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditingCollection(null)}>
                Cancel
              </Button>
              <Button
                onClick={handleUpdateCollection}
                disabled={!newCollectionName.trim()}
              >
                Save Changes
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}

/** Dropdown component to add a search to a collection. */
interface AddToCollectionDropdownProps {
  searchId: string;
  trigger?: React.ReactNode;
}

/** Dropdown component to add a search to a collection. */
export function AddToCollectionDropdown({
  searchId,
  trigger,
}: AddToCollectionDropdownProps) {
  const collections = useSearchCollections();
  const { addSearchToCollection, createCollection } = useSearchHistoryStore();
  const [isCreating, setIsCreating] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState("");

  const handleAddToCollection = (collectionId: string) => {
    addSearchToCollection(collectionId, searchId);
  };

  const handleCreateAndAdd = async () => {
    if (!newCollectionName.trim()) return;

    const collectionId = await createCollection(newCollectionName.trim());
    if (collectionId) {
      addSearchToCollection(collectionId, searchId);
      setNewCollectionName("");
      setIsCreating(false);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        {trigger || (
          <Button variant="ghost" size="sm">
            <PlusIcon className="h-4 w-4 mr-1" />
            Add to Collection
          </Button>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {collections.length > 0 ? (
          <>
            {collections.map((collection) => (
              <DropdownMenuItem
                key={collection.id}
                onClick={() => handleAddToCollection(collection.id)}
              >
                <FolderIcon className="h-4 w-4 mr-2" />
                {collection.name}
              </DropdownMenuItem>
            ))}
            <div className="border-t my-1" />
          </>
        ) : null}

        {isCreating ? (
          <div className="p-2 space-y-2">
            <Input
              placeholder="Collection name"
              value={newCollectionName}
              onChange={(e) => setNewCollectionName(e.target.value)}
              autoFocus
            />
            <div className="flex gap-1">
              <Button
                size="sm"
                variant="outline"
                className="flex-1"
                onClick={() => setIsCreating(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                className="flex-1"
                onClick={handleCreateAndAdd}
                disabled={!newCollectionName.trim()}
              >
                Create
              </Button>
            </div>
          </div>
        ) : (
          <DropdownMenuItem onClick={() => setIsCreating(true)}>
            <FolderPlusIcon className="h-4 w-4 mr-2" />
            New Collection
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
