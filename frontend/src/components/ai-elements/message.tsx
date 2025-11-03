/**
 * @fileoverview Message primitives for chat UIs. Includes container, content,
 * and avatar components used within conversation lists.
 */
import type { UIMessage } from "ai";
import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps, HTMLAttributes } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

/** Props for a single chat message container. */
export type MessageProps = HTMLAttributes<HTMLDivElement> & {
  from: UIMessage["role"];
};

/**
 * Message container that aligns based on author role.
 *
 * @param from The role of the message author (user or assistant).
 * @returns A flex container with appropriate alignment.
 */
export const Message = ({ className, from, ...props }: MessageProps) => (
  <div
    className={cn(
      "group flex w-full items-end justify-end gap-2 py-4",
      from === "user" ? "is-user" : "is-assistant flex-row-reverse justify-end",
      className
    )}
    {...props}
  />
);

const messageContentVariants = cva(
  "is-user:dark flex flex-col gap-2 overflow-hidden rounded-lg text-sm",
  {
    defaultVariants: {
      variant: "contained",
    },
    variants: {
      variant: {
        contained: [
          "max-w-[80%] px-4 py-3",
          "group-[.is-user]:bg-primary group-[.is-user]:text-primary-foreground",
          "group-[.is-assistant]:bg-secondary group-[.is-assistant]:text-foreground",
        ],
        flat: [
          "group-[.is-user]:max-w-[80%] group-[.is-user]:bg-secondary group-[.is-user]:px-4 group-[.is-user]:py-3 group-[.is-user]:text-foreground",
          "group-[.is-assistant]:text-foreground",
        ],
      },
    },
  }
);

/** Props for message content region. */
export type MessageContentProps = HTMLAttributes<HTMLDivElement> &
  VariantProps<typeof messageContentVariants>;

/**
 * Content wrapper for message text and elements.
 *
 * @param variant Visual variant (contained or flat).
 * @returns A styled content container.
 */
export const MessageContent = ({
  children,
  className,
  variant,
  ...props
}: MessageContentProps) => (
  <div className={cn(messageContentVariants({ className, variant }))} {...props}>
    {children}
  </div>
);

/** Props for the message avatar. */
export type MessageAvatarProps = ComponentProps<typeof Avatar> & {
  src: string;
  name?: string;
};

/**
 * Avatar for the message author.
 *
 * @param src Image URL.
 * @param name Optional display name for fallback initials.
 * @returns A sized avatar with border ring and fallback.
 */
export const MessageAvatar = ({
  src,
  name,
  className,
  ...props
}: MessageAvatarProps) => (
  <Avatar className={cn("size-8 ring-1 ring-border", className)} {...props}>
    <AvatarImage alt="" className="mt-0 mb-0" src={src} />
    <AvatarFallback>{name?.slice(0, 2) || "ME"}</AvatarFallback>
  </Avatar>
);
