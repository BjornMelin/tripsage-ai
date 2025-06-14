"use client";

import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { Check, ChevronsUpDown } from "lucide-react";
import { useState } from "react";

interface ServiceSelectorProps {
  services: string[];
  selectedService: string | null;
  onServiceChange: (service: string) => void;
  disabled?: boolean;
}

export function ServiceSelector({
  services,
  selectedService,
  onServiceChange,
  disabled = false,
}: ServiceSelectorProps) {
  const [open, setOpen] = useState(false);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          // biome-ignore lint/a11y/useSemanticElements: Custom combobox implementation using shadcn/ui
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between"
          disabled={disabled}
        >
          {selectedService
            ? services.find((service) => service === selectedService)
            : "Select service..."}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-full p-0">
        <Command>
          <CommandInput placeholder="Search service..." />
          <CommandEmpty>No service found.</CommandEmpty>
          <CommandGroup>
            {services.map((service) => (
              <CommandItem
                key={service}
                value={service}
                onSelect={() => {
                  onServiceChange(service);
                  setOpen(false);
                }}
              >
                <Check
                  className={cn(
                    "mr-2 h-4 w-4",
                    selectedService === service ? "opacity-100" : "opacity-0"
                  )}
                />
                {service}
              </CommandItem>
            ))}
          </CommandGroup>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
