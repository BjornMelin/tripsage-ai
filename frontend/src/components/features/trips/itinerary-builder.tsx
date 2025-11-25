"use client";

import {
  DragDropContext,
  Draggable,
  Droppable,
  type DropResult,
} from "@hello-pangea/dnd";
import {
  Calendar,
  Car,
  Edit2,
  GripVertical,
  Hotel,
  MapPin,
  Plane,
  Plus,
  Train,
  Trash2,
} from "lucide-react";
import type { Dispatch, SetStateAction } from "react";
import { useCallback, useId, useState } from "react";
import { Badge } from "@/components/ui/badge";
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
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { secureUuid } from "@/lib/security/random";
import { type Destination, type Trip, useTripStore } from "@/stores/trip-store";

interface ItineraryBuilderProps {
  trip: Trip;
  onUpdateTrip?: (trip: Trip) => void;
  className?: string;
}

interface DestinationFormData {
  name: string;
  country: string;
  startDate: string;
  endDate: string;
  activities: string[];
  accommodation: {
    type: string;
    name: string;
    price?: number;
  };
  transportation: {
    type: string;
    details: string;
    price?: number;
  };
  estimatedCost?: number;
  notes?: string;
}

interface DestinationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  formData: DestinationFormData;
  setFormData: Dispatch<SetStateAction<DestinationFormData>>;
  addActivity: () => void;
  updateActivity: (index: number, value: string) => void;
  removeActivity: (index: number) => void;
  onSave: () => Promise<void>;
  isEditing: boolean;
}

function DestinationDialog({
  isOpen,
  onClose,
  title,
  formData,
  setFormData,
  addActivity,
  updateActivity,
  removeActivity,
  onSave,
  isEditing,
}: DestinationDialogProps) {
  const nameInputId = useId();
  const countryInputId = useId();
  const startDateInputId = useId();
  const endDateInputId = useId();
  const transportationDetailsId = useId();
  const accommodationNameId = useId();
  const estimatedCostId = useId();
  const notesInputId = useId();

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            Fill in the details for this destination
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor={nameInputId}>Destination Name</Label>
              <Input
                id={nameInputId}
                value={formData.name}
                onChange={(event) =>
                  setFormData((prev) => ({ ...prev, name: event.target.value }))
                }
                placeholder="e.g., Paris"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor={countryInputId}>Country</Label>
              <Input
                id={countryInputId}
                value={formData.country}
                onChange={(event) =>
                  setFormData((prev) => ({
                    ...prev,
                    country: event.target.value,
                  }))
                }
                placeholder="e.g., France"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor={startDateInputId}>Start Date</Label>
              <Input
                id={startDateInputId}
                type="date"
                value={formData.startDate}
                onChange={(event) =>
                  setFormData((prev) => ({
                    ...prev,
                    startDate: event.target.value,
                  }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor={endDateInputId}>End Date</Label>
              <Input
                id={endDateInputId}
                type="date"
                value={formData.endDate}
                onChange={(event) =>
                  setFormData((prev) => ({
                    ...prev,
                    endDate: event.target.value,
                  }))
                }
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Transportation</Label>
            <div className="grid grid-cols-2 gap-4">
              <Select
                value={formData.transportation.type}
                onValueChange={(value) =>
                  setFormData((prev) => ({
                    ...prev,
                    transportation: { ...prev.transportation, type: value },
                  }))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select transport" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="flight">Flight</SelectItem>
                  <SelectItem value="car">Car</SelectItem>
                  <SelectItem value="train">Train</SelectItem>
                  <SelectItem value="bus">Bus</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
              <Input
                id={transportationDetailsId}
                placeholder="Transportation details"
                value={formData.transportation.details}
                onChange={(event) =>
                  setFormData((prev) => ({
                    ...prev,
                    transportation: {
                      ...prev.transportation,
                      details: event.target.value,
                    },
                  }))
                }
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Accommodation</Label>
            <div className="grid grid-cols-2 gap-4">
              <Select
                value={formData.accommodation.type}
                onValueChange={(value) =>
                  setFormData((prev) => ({
                    ...prev,
                    accommodation: { ...prev.accommodation, type: value },
                  }))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Accommodation type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="hotel">Hotel</SelectItem>
                  <SelectItem value="hostel">Hostel</SelectItem>
                  <SelectItem value="airbnb">Airbnb</SelectItem>
                  <SelectItem value="apartment">Apartment</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
              <Input
                id={accommodationNameId}
                placeholder="Accommodation name"
                value={formData.accommodation.name}
                onChange={(event) =>
                  setFormData((prev) => ({
                    ...prev,
                    accommodation: {
                      ...prev.accommodation,
                      name: event.target.value,
                    },
                  }))
                }
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Activities</Label>
              <Button type="button" variant="outline" size="sm" onClick={addActivity}>
                <Plus className="h-4 w-4 mr-1" />
                Add Activity
              </Button>
            </div>
            {formData.activities.map((activity, index) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: Activities are simple strings without stable IDs; index key avoids remount on input change
              <div key={`activity-${index}`} className="flex gap-2">
                <Input
                  value={activity}
                  onChange={(event) => updateActivity(index, event.target.value)}
                  placeholder="Activity description"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => removeActivity(index)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>

          <div className="space-y-2">
            <Label htmlFor={estimatedCostId}>Estimated Cost ($)</Label>
            <Input
              id={estimatedCostId}
              type="number"
              value={formData.estimatedCost ?? ""}
              onChange={(event) =>
                setFormData((prev) => ({
                  ...prev,
                  estimatedCost: event.target.value
                    ? Number.parseFloat(event.target.value)
                    : undefined,
                }))
              }
              placeholder="Optional"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor={notesInputId}>Notes</Label>
            <Textarea
              id={notesInputId}
              value={formData.notes}
              onChange={(event) =>
                setFormData((prev) => ({ ...prev, notes: event.target.value }))
              }
              placeholder="Additional notes or comments"
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={onSave}>{isEditing ? "Update" : "Add"} Destination</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ItineraryBuilder({
  trip,
  onUpdateTrip,
  className,
}: ItineraryBuilderProps) {
  const { updateTrip, addDestination, updateDestination, removeDestination } =
    useTripStore();
  const [isAddingDestination, setIsAddingDestination] = useState(false);
  const [editingDestination, setEditingDestination] = useState<Destination | null>(
    null
  );
  const [formData, setFormData] = useState<DestinationFormData>({
    accommodation: { name: "", type: "" },
    activities: [],
    country: "",
    endDate: "",
    estimatedCost: undefined,
    name: "",
    notes: "",
    startDate: "",
    transportation: { details: "", type: "" },
  });

  const handleDragEnd = useCallback(
    (result: DropResult) => {
      if (!result.destination) return;

      const items = Array.from(trip.destinations);
      const [reorderedItem] = items.splice(result.source.index, 1);
      items.splice(result.destination.index, 0, reorderedItem);

      const updatedTrip = { ...trip, destinations: items };

      if (onUpdateTrip) {
        onUpdateTrip(updatedTrip);
      } else {
        updateTrip(trip.id, { destinations: items });
      }
    },
    [trip, onUpdateTrip, updateTrip]
  );

  const resetForm = () => {
    setFormData({
      accommodation: { name: "", type: "" },
      activities: [],
      country: "",
      endDate: "",
      estimatedCost: undefined,
      name: "",
      notes: "",
      startDate: "",
      transportation: { details: "", type: "" },
    });
  };

  const openAddDialog = () => {
    resetForm();
    setIsAddingDestination(true);
  };

  const openEditDialog = (destination: Destination) => {
    setFormData({
      accommodation: destination.accommodation || { name: "", type: "" },
      activities: destination.activities || [],
      country: destination.country,
      endDate: destination.endDate || "",
      estimatedCost: destination.estimatedCost,
      name: destination.name,
      notes: destination.notes || "",
      startDate: destination.startDate || "",
      transportation: destination.transportation || { details: "", type: "" },
    });
    setEditingDestination(destination);
  };

  const handleSaveDestination = async () => {
    const destinationData: Partial<Destination> = {
      accommodation: formData.accommodation.name ? formData.accommodation : undefined,
      activities: formData.activities.length > 0 ? formData.activities : undefined,
      country: formData.country,
      endDate: formData.endDate || undefined,
      estimatedCost: formData.estimatedCost,
      name: formData.name,
      notes: formData.notes || undefined,
      startDate: formData.startDate || undefined,
      transportation: formData.transportation.details
        ? formData.transportation
        : undefined,
    };

    if (editingDestination) {
      await updateDestination(trip.id, editingDestination.id, destinationData);
      setEditingDestination(null);
    } else {
      await addDestination(trip.id, {
        ...destinationData,
        id: secureUuid(),
      } as Destination);
      setIsAddingDestination(false);
    }

    resetForm();
  };

  const handleDeleteDestination = async (destinationId: string) => {
    await removeDestination(trip.id, destinationId);
  };

  const addActivity = () => {
    setFormData((prev) => ({
      ...prev,
      activities: [...prev.activities, ""],
    }));
  };

  const updateActivity = (index: number, value: string) => {
    setFormData((prev) => ({
      ...prev,
      activities: prev.activities.map((activity, i) =>
        i === index ? value : activity
      ),
    }));
  };

  const removeActivity = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      activities: prev.activities.filter((_, i) => i !== index),
    }));
  };

  const getTransportationIcon = (type?: string) => {
    switch (type) {
      case "flight":
        return <Plane className="h-4 w-4" />;
      case "car":
        return <Car className="h-4 w-4" />;
      case "train":
        return <Train className="h-4 w-4" />;
      default:
        return <MapPin className="h-4 w-4" />;
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5" />
              Itinerary Builder
            </CardTitle>
            <CardDescription>Plan and organize your trip destinations</CardDescription>
          </div>
          <Button onClick={openAddDialog}>
            <Plus className="h-4 w-4 mr-2" />
            Add Destination
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {trip.destinations.length === 0 ? (
          <div className="text-center py-8">
            <MapPin className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground mb-4">
              No destinations added yet. Start building your itinerary!
            </p>
            <Button onClick={openAddDialog}>
              <Plus className="h-4 w-4 mr-2" />
              Add First Destination
            </Button>
          </div>
        ) : (
          <DragDropContext onDragEnd={handleDragEnd}>
            <Droppable droppableId="destinations">
              {(provided) => (
                <div
                  {...provided.droppableProps}
                  ref={provided.innerRef}
                  className="space-y-4"
                >
                  {trip.destinations.map((destination, index) => (
                    <Draggable
                      key={destination.id}
                      draggableId={destination.id}
                      index={index}
                    >
                      {(provided, snapshot) => (
                        <Card
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          className={`${snapshot.isDragging ? "shadow-lg" : ""}`}
                        >
                          <CardContent className="p-4">
                            <div className="flex items-start gap-4">
                              <div
                                {...provided.dragHandleProps}
                                className="mt-1 cursor-grab active:cursor-grabbing"
                              >
                                <GripVertical className="h-5 w-5 text-muted-foreground" />
                              </div>

                              <div className="flex-1 space-y-2">
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <h4 className="font-semibold">
                                      {destination.name}
                                    </h4>
                                    <Badge variant="outline">
                                      {destination.country}
                                    </Badge>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => openEditDialog(destination)}
                                    >
                                      <Edit2 className="h-4 w-4" />
                                    </Button>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() =>
                                        handleDeleteDestination(destination.id)
                                      }
                                      className="text-destructive hover:text-destructive"
                                    >
                                      <Trash2 className="h-4 w-4" />
                                    </Button>
                                  </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4 text-sm text-muted-foreground">
                                  {destination.startDate && destination.endDate && (
                                    <div className="flex items-center gap-1">
                                      <Calendar className="h-4 w-4" />
                                      <span>
                                        {destination.startDate} - {destination.endDate}
                                      </span>
                                    </div>
                                  )}

                                  {destination.transportation && (
                                    <div className="flex items-center gap-1">
                                      {getTransportationIcon(
                                        destination.transportation.type
                                      )}
                                      <span>{destination.transportation.details}</span>
                                    </div>
                                  )}

                                  {destination.accommodation && (
                                    <div className="flex items-center gap-1">
                                      <Hotel className="h-4 w-4" />
                                      <span>{destination.accommodation.name}</span>
                                    </div>
                                  )}

                                  {destination.estimatedCost && (
                                    <div className="flex items-center gap-1">
                                      <span>Cost: ${destination.estimatedCost}</span>
                                    </div>
                                  )}
                                </div>

                                {destination.activities &&
                                  destination.activities.length > 0 && (
                                    <div>
                                      <p className="text-sm font-medium mb-1">
                                        Activities:
                                      </p>
                                      <div className="flex flex-wrap gap-1">
                                        {destination.activities.map(
                                          (activity, _actIndex) => (
                                            <Badge
                                              key={activity}
                                              variant="secondary"
                                              className="text-xs"
                                            >
                                              {activity}
                                            </Badge>
                                          )
                                        )}
                                      </div>
                                    </div>
                                  )}

                                {destination.notes && (
                                  <p className="text-sm text-muted-foreground italic">
                                    {destination.notes}
                                  </p>
                                )}
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </div>
              )}
            </Droppable>
          </DragDropContext>
        )}
      </CardContent>

      {/* Add Destination Dialog */}
      <DestinationDialog
        isOpen={isAddingDestination}
        onClose={() => setIsAddingDestination(false)}
        title="Add New Destination"
        formData={formData}
        setFormData={setFormData}
        addActivity={addActivity}
        updateActivity={updateActivity}
        removeActivity={removeActivity}
        onSave={handleSaveDestination}
        isEditing={false}
      />

      {/* Edit Destination Dialog */}
      <DestinationDialog
        isOpen={!!editingDestination}
        onClose={() => setEditingDestination(null)}
        title="Edit Destination"
        formData={formData}
        setFormData={setFormData}
        addActivity={addActivity}
        updateActivity={updateActivity}
        removeActivity={removeActivity}
        onSave={handleSaveDestination}
        isEditing={Boolean(editingDestination)}
      />
    </Card>
  );
}
