"use client";

import * as ToggleGroupPrimitive from "@radix-ui/react-toggle-group";
import type { VariantProps } from "class-variance-authority";
import * as React from "react";
import { ToggleVariants } from "@/components/ui/toggle";
import { cn } from "@/lib/utils";

const ToggleGroupContext = React.createContext<VariantProps<typeof ToggleVariants>>({
  size: "default",
  variant: "default",
});

const ToggleGroup = React.forwardRef<
  React.ElementRef<typeof ToggleGroupPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ToggleGroupPrimitive.Root> &
    VariantProps<typeof ToggleVariants>
>(({ className, variant, size, children, type = "single", ...props }, ref) => {
  const baseClassName = cn("flex items-center justify-center gap-1", className);

  if (type === "multiple") {
    const multipleProps = props as Omit<
      ToggleGroupPrimitive.ToggleGroupMultipleProps,
      "type"
    >;
    return (
      <ToggleGroupPrimitive.Root
        ref={ref}
        type="multiple"
        className={baseClassName}
        {...multipleProps}
      >
        <ToggleGroupContext.Provider value={{ size, variant }}>
          {children}
        </ToggleGroupContext.Provider>
      </ToggleGroupPrimitive.Root>
    );
  }

  const singleProps = props as Omit<
    ToggleGroupPrimitive.ToggleGroupSingleProps,
    "type"
  >;

  return (
    <ToggleGroupPrimitive.Root
      ref={ref}
      type="single"
      className={baseClassName}
      {...singleProps}
    >
      <ToggleGroupContext.Provider value={{ size, variant }}>
        {children}
      </ToggleGroupContext.Provider>
    </ToggleGroupPrimitive.Root>
  );
});

ToggleGroup.displayName = ToggleGroupPrimitive.Root.displayName;

const ToggleGroupItem = React.forwardRef<
  React.ElementRef<typeof ToggleGroupPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof ToggleGroupPrimitive.Item> &
    VariantProps<typeof ToggleVariants>
>(({ className, children, variant, size, value, ...props }, ref) => {
  const context = React.useContext(ToggleGroupContext);

  return (
    <ToggleGroupPrimitive.Item
      ref={ref}
      value={value}
      className={cn(
        ToggleVariants({
          size: context.size || size,
          variant: context.variant || variant,
        }),
        className
      )}
      {...props}
    >
      {children}
    </ToggleGroupPrimitive.Item>
  );
});

ToggleGroupItem.displayName = ToggleGroupPrimitive.Item.displayName;

export { ToggleGroup, ToggleGroupItem };
