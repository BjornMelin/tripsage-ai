/**
 * @fileoverview Polymorphic component types for React.
 * Provides a type for polymorphic components with a generic element type.
 */
import type * as React from "react";

/**
 * Type for the element reference of a polymorphic component.
 *
 * @param E The element type.
 * @returns The element reference type.
 */
export type ElementRef<E extends React.ElementType> =
  React.ComponentPropsWithRef<E>["ref"] extends React.Ref<infer R> ? R : never;

/**
 * Type for the props of a polymorphic component.
 *
 * @param E The element type.
 * @returns The props type.
 */
export type PropsOf<E extends React.ElementType> = React.ComponentPropsWithoutRef<E>;

/**
 * Type for the props of a polymorphic component.
 *
 * @param E The element type.
 * @param P The props type.
 * @returns The props type.
 */
export type PolymorphicProps<
  E extends React.ElementType,
  P = Record<string, never>,
> = P & {
  as?: E;
  ref?: React.Ref<ElementRef<E>>;
} & Omit<PropsOf<E>, "as" | "ref">;
