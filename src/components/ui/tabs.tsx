"use client";

import * as TabsPrimitive from "@radix-ui/react-tabs";
import type * as React from "react";

import { cn } from "@/lib/utils";

/** Root tabs container backed by Radix UI. */
export const Tabs = TabsPrimitive.Root;

/** Props for the tabs list container. */
export interface TabsListProps
  extends React.ComponentPropsWithoutRef<typeof TabsPrimitive.List> {
  ref?: React.Ref<React.ComponentRef<typeof TabsPrimitive.List>>;
}
/**
 * Renders the tabs list container.
 *
 * @param props - Props forwarded to the Radix tabs list.
 * @returns The tabs list element.
 */
export function TabsList(props: TabsListProps) {
  const { className, ref, ...rest } = props;
  return (
    <TabsPrimitive.List
      ref={ref}
      className={cn(
        "inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground",
        className
      )}
      {...rest}
    />
  );
}
TabsList.displayName = TabsPrimitive.List.displayName;

/** Props for a tabs trigger button. */
export interface TabsTriggerProps
  extends React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger> {
  ref?: React.Ref<React.ComponentRef<typeof TabsPrimitive.Trigger>>;
}
/**
 * Renders a tabs trigger button.
 *
 * @param props - Props forwarded to the Radix tabs trigger.
 * @returns The tabs trigger element.
 */
export function TabsTrigger(props: TabsTriggerProps) {
  const { className, ref, ...rest } = props;
  return (
    <TabsPrimitive.Trigger
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-[color,background-color,box-shadow] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm",
        className
      )}
      {...rest}
    />
  );
}
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

/** Props for tabs content panels. */
export interface TabsContentProps
  extends React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content> {
  ref?: React.Ref<React.ComponentRef<typeof TabsPrimitive.Content>>;
}
/**
 * Renders a tabs content panel.
 *
 * @param props - Props forwarded to the Radix tabs content.
 * @returns The tabs content element.
 */
export function TabsContent(props: TabsContentProps) {
  const { className, ref, ...rest } = props;
  return (
    <TabsPrimitive.Content
      ref={ref}
      className={cn(
        "mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        className
      )}
      {...rest}
    />
  );
}
TabsContent.displayName = TabsPrimitive.Content.displayName;
