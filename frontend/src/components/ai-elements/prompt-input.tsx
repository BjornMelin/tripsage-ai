/**
 * @fileoverview Prompt input components for AI chat interfaces. Provides input forms
 * with file attachments, drag-and-drop, and form submission handling.
 */

"use client";

import type { ChatStatus, FileUIPart } from "ai";
import {
  ImageIcon,
  Loader2Icon,
  MicIcon,
  PaperclipIcon,
  PlusIcon,
  SendIcon,
  SquareIcon,
  XIcon,
} from "lucide-react";
import { nanoid } from "nanoid";
import {
  type ChangeEvent,
  type ChangeEventHandler,
  Children,
  type ClipboardEventHandler,
  type ComponentProps,
  createContext,
  type FormEvent,
  type FormEventHandler,
  Fragment,
  type HTMLAttributes,
  type KeyboardEventHandler,
  type PropsWithChildren,
  type ReactNode,
  type RefObject,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from "@/components/ui/input-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
// Provider Context & Types ----------------------------------------------------

/**
 * Context interface for managing file attachments in prompt input components.
 */
export type AttachmentsContext = {
  /** Array of attached files with unique IDs. */
  files: (FileUIPart & { id: string })[];
  /** Adds one or more files to the attachments. */
  add: (files: File[] | FileList) => void;
  /** Removes an attachment by its unique ID. */
  remove: (id: string) => void;
  /** Clears all attachments. */
  clear: () => void;
  /** Opens the file selection dialog. */
  openFileDialog: () => void;
  /** Reference to the hidden file input element. */
  fileInputRef: RefObject<HTMLInputElement | null>;
};

/**
 * Context interface for managing text input state in prompt input components.
 */
export type TextInputContext = {
  /** Current text input value. */
  value: string;
  /** Sets the text input value. */
  setInput: (v: string) => void;
  /** Clears the text input. */
  clear: () => void;
};

/**
 * Props for the PromptInputController context provider.
 */
export type PromptInputControllerProps = {
  /** Text input context for managing input state. */
  textInput: TextInputContext;
  /** Attachments context for managing file attachments. */
  attachments: AttachmentsContext;
  /** INTERNAL: Allows PromptInput to register its file input ref and open callback. */
  __registerFileInput: (
    ref: RefObject<HTMLInputElement | null>,
    open: () => void
  ) => void;
};

const PromptInputController = createContext<PromptInputControllerProps | null>(null);
const ProviderAttachmentsContext = createContext<AttachmentsContext | null>(null);

/**
 * Hook to access the PromptInputController context.
 *
 * @returns The PromptInputController context.
 * @throws An error if the context is not found.
 */
export const usePromptInputController = () => {
  const ctx = useContext(PromptInputController);
  if (!ctx) {
    throw new Error(
      "Wrap your component inside <PromptInputProvider> to use usePromptInputController()."
    );
  }
  return ctx;
};

// Optional variants (do NOT throw). Useful for dual-mode components.
const useOptionalPromptInputController = () => useContext(PromptInputController);

/**
 * Hook to access the ProviderAttachmentsContext context.
 *
 * @returns The ProviderAttachmentsContext context.
 * @throws An error if the context is not found.
 */
export const useProviderAttachments = () => {
  const ctx = useContext(ProviderAttachmentsContext);
  if (!ctx) {
    throw new Error(
      "Wrap your component inside <PromptInputProvider> to use useProviderAttachments()."
    );
  }
  return ctx;
};

const useOptionalProviderAttachments = () => useContext(ProviderAttachmentsContext);

/**
 * Props for the PromptInputProvider component.
 */
export type PromptInputProviderProps = PropsWithChildren<{
  /** Initial text input value. Defaults to empty string. */
  initialInput?: string;
}>;

/**
 * Optional global provider that lifts PromptInput state outside of PromptInput.
 * If you don't use it, PromptInput stays fully self-managed.
 *
 * @param initialInput Initial text input value. Defaults to empty string.
 * @param children Child components to render.
 * @returns Provider component wrapping children with PromptInput contexts.
 */
export function PromptInputProvider({
  initialInput: initialTextInput = "",
  children,
}: PromptInputProviderProps) {
  // ----- textInput state
  const [textInput, setTextInput] = useState(initialTextInput);
  const clearInput = useCallback(() => setTextInput(""), []);

  // ----- attachments state (global when wrapped)
  const [attachements, setAttachements] = useState<(FileUIPart & { id: string })[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const openRef = useRef<() => void>(() => {
    // Initial empty function, will be replaced by __registerFileInput
  });

  const add = useCallback((files: File[] | FileList) => {
    const incoming = Array.from(files);
    if (incoming.length === 0) return;

    setAttachements((prev) =>
      prev.concat(
        incoming.map((file) => ({
          filename: file.name,
          id: nanoid(),
          mediaType: file.type,
          type: "file" as const,
          url: URL.createObjectURL(file),
        }))
      )
    );
  }, []);

  const remove = useCallback((id: string) => {
    setAttachements((prev) => {
      const found = prev.find((f) => f.id === id);
      if (found?.url) URL.revokeObjectURL(found.url);
      return prev.filter((f) => f.id !== id);
    });
  }, []);

  const clear = useCallback(() => {
    setAttachements((prev) => {
      for (const f of prev) if (f.url) URL.revokeObjectURL(f.url);
      return [];
    });
  }, []);

  const openFileDialog = useCallback(() => {
    openRef.current?.();
  }, []);

  const attachments = useMemo<AttachmentsContext>(
    () => ({
      add,
      clear,
      fileInputRef,
      files: attachements,
      openFileDialog,
      remove,
    }),
    [attachements, add, remove, clear, openFileDialog]
  );

  const __registerFileInput = useCallback(
    (ref: RefObject<HTMLInputElement | null>, open: () => void) => {
      fileInputRef.current = ref.current;
      openRef.current = open;
    },
    []
  );

  const controller = useMemo<PromptInputControllerProps>(
    () => ({
      __registerFileInput,
      attachments,
      textInput: {
        clear: clearInput,
        setInput: setTextInput,
        value: textInput,
      },
    }),
    [textInput, clearInput, attachments, __registerFileInput]
  );

  return (
    <PromptInputController.Provider value={controller}>
      <ProviderAttachmentsContext.Provider value={attachments}>
        {children}
      </ProviderAttachmentsContext.Provider>
    </PromptInputController.Provider>
  );
}

// Component Context & Hooks ---------------------------------------------------

const LocalAttachmentsContext = createContext<AttachmentsContext | null>(null);

/**
 * Hook to access the attachments context.
 *
 * @returns The attachments context.
 * @throws An error if the context is not found.
 */
export const usePromptInputAttachments = () => {
  // Dual-mode: prefer provider if present, otherwise use local
  const provider = useOptionalProviderAttachments();
  const local = useContext(LocalAttachmentsContext);
  const context = provider ?? local;
  if (!context) {
    throw new Error(
      "usePromptInputAttachments must be used within a PromptInput or PromptInputProvider"
    );
  }
  return context;
};

/**
 * Props for the PromptInputAttachment component.
 */
export type PromptInputAttachmentProps = HTMLAttributes<HTMLDivElement> & {
  /** The attachment data including file information and unique ID. */
  data: FileUIPart & { id: string };
  /** Optional additional CSS classes. */
  className?: string;
};

/**
 * Component for displaying a file or image attachment with preview and removal functionality.
 *
 * @param data The attachment data including file information and unique ID.
 * @param className Optional additional CSS classes.
 * @param props Additional HTML div element props.
 * @returns A hover card containing the attachment preview with remove button.
 */
export function PromptInputAttachment({
  data,
  className,
  ...props
}: PromptInputAttachmentProps) {
  const attachments = usePromptInputAttachments();

  const filename = data.filename || "";

  const mediaType = data.mediaType?.startsWith("image/") && data.url ? "image" : "file";
  const isImage = mediaType === "image";

  const attachmentLabel = filename || (isImage ? "Image" : "Attachment");

  return (
    <PromptInputHoverCard>
      <HoverCardTrigger asChild>
        <div
          className={cn(
            "group relative flex h-8 cursor-default select-none items-center gap-1.5 rounded-md border border-border px-1.5 font-medium text-sm transition-all hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/50",
            className
          )}
          key={data.id}
          {...props}
        >
          <div className="relative size-5 shrink-0">
            <div className="absolute inset-0 flex size-5 items-center justify-center overflow-hidden rounded bg-background transition-opacity group-hover:opacity-0">
              {isImage ? (
                <img
                  alt={filename || "attachment"}
                  className="size-5 object-cover"
                  height={20}
                  src={data.url}
                  width={20}
                />
              ) : (
                <div className="flex size-5 items-center justify-center text-muted-foreground">
                  <PaperclipIcon className="size-3" />
                </div>
              )}
            </div>
            <Button
              aria-label="Remove attachment"
              className="absolute inset-0 size-5 cursor-pointer rounded p-0 opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100 [&>svg]:size-2.5"
              onClick={(e) => {
                e.stopPropagation();
                attachments.remove(data.id);
              }}
              type="button"
              variant="ghost"
            >
              <XIcon />
              <span className="sr-only">Remove</span>
            </Button>
          </div>

          <span className="flex-1 truncate">{attachmentLabel}</span>
        </div>
      </HoverCardTrigger>
      <PromptInputHoverCardContent className="w-auto p-2">
        <div className="w-auto space-y-3">
          {isImage && (
            <div className="flex max-h-96 w-96 items-center justify-center overflow-hidden rounded-md border">
              <img
                alt={filename || "attachment preview"}
                className="max-h-full max-w-full object-contain"
                height={384}
                src={data.url}
                width={448}
              />
            </div>
          )}
          <div className="flex items-center gap-2.5">
            <div className="min-w-0 flex-1 space-y-1 px-0.5">
              <h4 className="truncate font-semibold text-sm leading-none">
                {filename || (isImage ? "Image" : "Attachment")}
              </h4>
              {data.mediaType && (
                <p className="truncate font-mono text-muted-foreground text-xs">
                  {data.mediaType}
                </p>
              )}
            </div>
          </div>
        </div>
      </PromptInputHoverCardContent>
    </PromptInputHoverCard>
  );
}

/**
 * Props for the PromptInputAttachments component.
 */
export type PromptInputAttachmentsProps = Omit<
  HTMLAttributes<HTMLDivElement>,
  "children"
> & {
  /** Render function for each attachment. */
  children: (attachment: FileUIPart & { id: string }) => ReactNode;
};

/**
 * Container component that renders all current attachments using a render prop pattern.
 * Only renders when there are attachments to display.
 *
 * @param children Render function that receives each attachment and returns JSX.
 * @returns Fragment containing rendered attachments, or null if no attachments exist.
 */
export function PromptInputAttachments({ children }: PromptInputAttachmentsProps) {
  const attachments = usePromptInputAttachments();

  if (!attachments.files.length) {
    return null;
  }

  return attachments.files.map((file) => (
    <Fragment key={file.id}>{children(file)}</Fragment>
  ));
}

/**
 * Props for the PromptInputActionAddAttachments component.
 */
export type PromptInputActionAddAttachmentsProps = ComponentProps<
  typeof DropdownMenuItem
> & {
  /** Optional label for the add attachments action. */
  label?: string;
};

/**
 * Dropdown menu item component that triggers the file selection dialog.
 * Integrates with PromptInput's attachment system for adding files/photos.
 *
 * @param label Optional custom label text. Defaults to "Add photos or files".
 * @param props Additional dropdown menu item props.
 * @returns Dropdown menu item that opens file selection when clicked.
 */
export const PromptInputActionAddAttachments = ({
  label = "Add photos or files",
  ...props
}: PromptInputActionAddAttachmentsProps) => {
  const attachments = usePromptInputAttachments();

  return (
    <DropdownMenuItem
      {...props}
      onSelect={(e) => {
        e.preventDefault();
        attachments.openFileDialog();
      }}
    >
      <ImageIcon className="mr-2 size-4" /> {label}
    </DropdownMenuItem>
  );
};

/**
 * Message data structure for prompt input submissions.
 */
export type PromptInputMessage = {
  /** Optional text content of the message. */
  text?: string;
  /** Optional array of attached files. */
  files?: FileUIPart[];
};

/**
 * Props for the PromptInput component.
 */
export type PromptInputProps = Omit<
  HTMLAttributes<HTMLFormElement>,
  "onSubmit" | "onError"
> & {
  /** File accept pattern (e.g., "image/*"). Leave undefined for any file type. */
  accept?: string;
  /** Whether multiple files can be selected. */
  multiple?: boolean;
  /** When true, accepts drops anywhere on document. Default false (opt-in). */
  globalDrop?: boolean;
  /** Render a hidden input with given name and keep it in sync for native form posts. Default false. */
  syncHiddenInput?: boolean;
  /** Maximum number of files allowed. */
  maxFiles?: number;
  /** Maximum file size in bytes. */
  maxFileSize?: number;
  /** Error handler for file validation failures. */
  onError?: (err: {
    code: "max_files" | "max_file_size" | "accept";
    message: string;
  }) => void;
  /** Submit handler for the prompt input. */
  onSubmit: (
    message: PromptInputMessage,
    event: FormEvent<HTMLFormElement>
  ) => void | Promise<void>;
};

/**
 * Main prompt input component for AI chat interfaces. Provides a form
 * with file attachments, drag-and-drop, and input controls.
 *
 * @param accept File accept pattern (e.g., "image/*"). Leave undefined for any file type.
 * @param multiple Whether multiple files can be selected.
 * @param globalDrop When true, accepts drops anywhere on document. Default false (opt-in).
 * @param syncHiddenInput Whether to render a hidden input synced for native form posts. Default false.
 * @param maxFiles Maximum number of files allowed.
 * @param maxFileSize Maximum file size in bytes.
 * @param onError Error handler for file validation failures.
 * @param onSubmit Submit handler for the prompt input.
 * @param className Optional additional CSS classes.
 * @param children Child components to render within the form.
 * @param props Additional HTML form element props.
 * @returns A form element containing the prompt input interface.
 */
export const PromptInput = ({
  className,
  accept,
  multiple,
  globalDrop,
  syncHiddenInput,
  maxFiles,
  maxFileSize,
  onError,
  onSubmit,
  children,
  ...props
}: PromptInputProps) => {
  // Try to use a provider controller if present
  const controller = useOptionalPromptInputController();
  const usingProvider = !!controller;

  const inputRef = useRef<HTMLInputElement | null>(null);
  const anchorRef = useRef<HTMLSpanElement>(null);
  const formRef = useRef<HTMLFormElement | null>(null);

  // Find nearest form to scope drag & drop
  useEffect(() => {
    const root = anchorRef.current?.closest("form");
    if (root instanceof HTMLFormElement) {
      formRef.current = root;
    }
  }, []);

  // ----- Local attachments (only used when no provider)
  const [items, setItems] = useState<(FileUIPart & { id: string })[]>([]);
  const files = usingProvider ? controller.attachments.files : items;

  // Opens the hidden file input dialog when no provider is available
  const openFileDialogLocal = useCallback(() => {
    inputRef.current?.click();
  }, []);

  // Validates if a file matches the accept pattern (simplified implementation)
  const matchesAccept = useCallback(
    (f: File) => {
      if (!accept || accept.trim() === "") {
        return true;
      }
      if (accept.includes("image/*")) {
        return f.type.startsWith("image/");
      }
      // NOTE: keep simple; expand as needed for more complex accept patterns
      return true;
    },
    [accept]
  );

  // Adds files to local state with validation and capacity limits (when no provider)
  const addLocal = useCallback(
    (fileList: File[] | FileList) => {
      const incoming = Array.from(fileList);
      const accepted = incoming.filter((f) => matchesAccept(f));
      if (incoming.length && accepted.length === 0) {
        onError?.({
          code: "accept",
          message: "No files match the accepted types.",
        });
        return;
      }
      const withinSize = (f: File) => (maxFileSize ? f.size <= maxFileSize : true);
      const sized = accepted.filter(withinSize);
      if (accepted.length > 0 && sized.length === 0) {
        onError?.({
          code: "max_file_size",
          message: "All files exceed the maximum size.",
        });
        return;
      }

      setItems((prev) => {
        const capacity =
          typeof maxFiles === "number"
            ? Math.max(0, maxFiles - prev.length)
            : undefined;
        const capped = typeof capacity === "number" ? sized.slice(0, capacity) : sized;
        if (typeof capacity === "number" && sized.length > capacity) {
          onError?.({
            code: "max_files",
            message: "Too many files. Some were not added.",
          });
        }
        const next: (FileUIPart & { id: string })[] = [];
        for (const file of capped) {
          next.push({
            filename: file.name,
            id: nanoid(),
            mediaType: file.type,
            type: "file",
            url: URL.createObjectURL(file),
          });
        }
        return prev.concat(next);
      });
    },
    [matchesAccept, maxFiles, maxFileSize, onError]
  );

  const add = usingProvider
    ? (files: File[] | FileList) => controller.attachments.add(files)
    : addLocal;

  const remove = usingProvider
    ? (id: string) => controller.attachments.remove(id)
    : (id: string) =>
        setItems((prev) => {
          const found = prev.find((file) => file.id === id);
          if (found?.url) {
            URL.revokeObjectURL(found.url);
          }
          return prev.filter((file) => file.id !== id);
        });

  const clear = usingProvider
    ? () => controller.attachments.clear()
    : () =>
        setItems((prev) => {
          for (const file of prev) {
            if (file.url) {
              URL.revokeObjectURL(file.url);
            }
          }
          return [];
        });

  const openFileDialog = usingProvider
    ? () => controller.attachments.openFileDialog()
    : openFileDialogLocal;

  // Let provider know about our hidden file input so external menus can call openFileDialog()
  useEffect(() => {
    if (!usingProvider) return;
    controller.__registerFileInput(inputRef, () => inputRef.current?.click());
  }, [usingProvider, controller]);

  // Note: File input cannot be programmatically set for security reasons
  // The syncHiddenInput prop is no longer functional
  useEffect(() => {
    if (syncHiddenInput && inputRef.current && files.length === 0) {
      inputRef.current.value = "";
    }
  }, [files, syncHiddenInput]);

  // Attach drop handlers on nearest form and document (opt-in)
  useEffect(() => {
    const form = formRef.current;
    if (!form) return;

    const onDragOver = (e: DragEvent) => {
      if (e.dataTransfer?.types?.includes("Files")) {
        e.preventDefault();
      }
    };
    const onDrop = (e: DragEvent) => {
      if (e.dataTransfer?.types?.includes("Files")) {
        e.preventDefault();
      }
      if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
        add(e.dataTransfer.files);
      }
    };
    form.addEventListener("dragover", onDragOver);
    form.addEventListener("drop", onDrop);
    return () => {
      form.removeEventListener("dragover", onDragOver);
      form.removeEventListener("drop", onDrop);
    };
  }, [add]);

  useEffect(() => {
    if (!globalDrop) return;

    const onDragOver = (e: DragEvent) => {
      if (e.dataTransfer?.types?.includes("Files")) {
        e.preventDefault();
      }
    };
    const onDrop = (e: DragEvent) => {
      if (e.dataTransfer?.types?.includes("Files")) {
        e.preventDefault();
      }
      if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
        add(e.dataTransfer.files);
      }
    };
    document.addEventListener("dragover", onDragOver);
    document.addEventListener("drop", onDrop);
    return () => {
      document.removeEventListener("dragover", onDragOver);
      document.removeEventListener("drop", onDrop);
    };
  }, [add, globalDrop]);

  useEffect(
    () => () => {
      if (!usingProvider) {
        for (const f of files) {
          if (f.url) URL.revokeObjectURL(f.url);
        }
      }
    },
    [usingProvider, files]
  );

  const handleChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    if (event.currentTarget.files) {
      add(event.currentTarget.files);
    }
  };

  // Converts blob URLs to data URLs for form submission compatibility
  const convertBlobUrlToDataUrl = async (url: string): Promise<string> => {
    const response = await fetch(url);
    const blob = await response.blob();
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  };

  const ctx = useMemo<AttachmentsContext>(
    () => ({
      add,
      clear,
      fileInputRef: inputRef,
      files: files.map((item) => ({ ...item, id: item.id })),
      openFileDialog,
      remove,
    }),
    [files, add, remove, clear, openFileDialog]
  );

  const handleSubmit: FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();

    const form = event.currentTarget;
    const text = usingProvider
      ? controller.textInput.value
      : (() => {
          const formData = new FormData(form);
          return (formData.get("message") as string) || "";
        })();

    // Reset form immediately after capturing text to avoid race condition
    // where user input during async blob conversion would be lost
    if (!usingProvider) {
      form.reset();
    }

    // Convert blob URLs to data URLs asynchronously
    Promise.all(
      files.map(async (file) => {
        const { id, ...item } = file;
        if (item.url && item.url.startsWith("blob:")) {
          return {
            id,
            ...item,
            url: await convertBlobUrlToDataUrl(item.url),
          };
        }
        return file;
      })
    ).then((convertedFiles: FileUIPart[]) => {
      try {
        const result = onSubmit({ files: convertedFiles, text }, event);

        // Handle both sync and async onSubmit
        if (result instanceof Promise) {
          result
            .then(() => {
              clear();
              if (usingProvider) {
                controller.textInput.clear();
              }
            })
            .catch(() => {
              // Don't clear on error - user may want to retry
            });
        } else {
          // Sync function completed without throwing, clear attachments
          clear();
          if (usingProvider) {
            controller.textInput.clear();
          }
        }
      } catch (error) {
        // Don't clear on error - user may want to retry
      }
    });
  };

  // Render with or without local provider
  const inner = (
    <>
      <span aria-hidden="true" className="hidden" ref={anchorRef} />
      <input
        accept={accept}
        aria-label="Upload files"
        className="hidden"
        multiple={multiple}
        onChange={handleChange}
        ref={inputRef}
        title="Upload files"
        type="file"
      />
      <form className={cn("w-full", className)} onSubmit={handleSubmit} {...props}>
        <InputGroup>{children}</InputGroup>
      </form>
    </>
  );

  return usingProvider ? (
    inner
  ) : (
    <LocalAttachmentsContext.Provider value={ctx}>
      {inner}
    </LocalAttachmentsContext.Provider>
  );
};

/**
 * Props for the PromptInputBody component.
 */
export type PromptInputBodyProps = HTMLAttributes<HTMLDivElement>;

/**
 * Semantic container for the main content area of the prompt input.
 * Provides consistent spacing and layout structure for input elements.
 *
 * @param className Optional additional CSS classes.
 * @param props Additional HTML div element props.
 * @returns Styled div element with "contents" class for layout purposes.
 */
export const PromptInputBody = ({ className, ...props }: PromptInputBodyProps) => (
  <div className={cn("contents", className)} {...props} />
);

/**
 * Props for the PromptInputTextarea component.
 */
export type PromptInputTextareaProps = ComponentProps<typeof InputGroupTextarea> & {
  /** Placeholder text for the textarea. */
  placeholder?: string;
};

/**
 * Textarea component with keyboard shortcuts and paste handling for attachments.
 * Supports Enter to submit (Shift+Enter for new line) and Backspace to remove attachments.
 * Handles file paste operations for drag-and-drop workflow.
 *
 * @param onChange Optional change handler (only used when not controlled by provider).
 * @param className Optional additional CSS classes.
 * @param placeholder Placeholder text for empty state.
 * @param props Additional textarea element props.
 * @returns Controlled or uncontrolled textarea with attachment integration.
 */
export const PromptInputTextarea = ({
  onChange,
  className,
  placeholder = "What would you like to know?",
  ...props
}: PromptInputTextareaProps) => {
  const controller = useOptionalPromptInputController();
  const attachments = usePromptInputAttachments();
  const [isComposing, setIsComposing] = useState(false);

  const handleKeyDown: KeyboardEventHandler<HTMLTextAreaElement> = (e) => {
    if (e.key === "Enter") {
      if (isComposing || e.nativeEvent.isComposing) {
        return;
      }
      if (e.shiftKey) {
        return;
      }
      e.preventDefault();
      e.currentTarget.form?.requestSubmit();
    }

    // Remove last attachment when Backspace is pressed and textarea is empty
    if (
      e.key === "Backspace" &&
      e.currentTarget.value === "" &&
      attachments.files.length > 0
    ) {
      e.preventDefault();
      const lastAttachment = attachments.files.at(-1);
      if (lastAttachment) {
        attachments.remove(lastAttachment.id);
      }
    }
  };

  const handlePaste: ClipboardEventHandler<HTMLTextAreaElement> = (event) => {
    const items = event.clipboardData?.items;

    if (!items) {
      return;
    }

    const files: File[] = [];

    for (const item of items) {
      if (item.kind === "file") {
        const file = item.getAsFile();
        if (file) {
          files.push(file);
        }
      }
    }

    if (files.length > 0) {
      event.preventDefault();
      attachments.add(files);
    }
  };

  const controlledProps = controller
    ? {
        onChange: (e: ChangeEvent<HTMLTextAreaElement>) => {
          controller.textInput.setInput(e.currentTarget.value);
          onChange?.(e);
        },
        value: controller.textInput.value,
      }
    : {
        onChange,
      };

  return (
    <InputGroupTextarea
      className={cn("field-sizing-content max-h-48 min-h-16", className)}
      name="message"
      onCompositionEnd={() => setIsComposing(false)}
      onCompositionStart={() => setIsComposing(true)}
      onKeyDown={handleKeyDown}
      onPaste={handlePaste}
      placeholder={placeholder}
      {...props}
      {...controlledProps}
    />
  );
};

/**
 * Props for the PromptInputHeader component.
 */
export type PromptInputHeaderProps = Omit<
  ComponentProps<typeof InputGroupAddon>,
  "align"
>;

/**
 * Layout component for header content above the input area.
 * Uses flexbox with wrap for responsive arrangement of header elements.
 *
 * @param className Optional additional CSS classes.
 * @param props Additional addon props.
 * @returns InputGroupAddon positioned at the start with flex-wrap styling.
 */
export const PromptInputHeader = ({ className, ...props }: PromptInputHeaderProps) => (
  <InputGroupAddon
    align="block-end"
    className={cn("order-first flex-wrap gap-1", className)}
    {...props}
  />
);

/**
 * Props for the PromptInputFooter component.
 */
export type PromptInputFooterProps = Omit<
  ComponentProps<typeof InputGroupAddon>,
  "align"
>;

/**
 * Layout component for footer content below the input area.
 * Uses space-between justification for left/right aligned footer elements.
 *
 * @param className Optional additional CSS classes.
 * @param props Additional addon props.
 * @returns InputGroupAddon with space-between justification for footer layout.
 */
export const PromptInputFooter = ({ className, ...props }: PromptInputFooterProps) => (
  <InputGroupAddon
    align="block-end"
    className={cn("justify-between gap-1", className)}
    {...props}
  />
);

/**
 * Props for the PromptInputTools component.
 */
export type PromptInputToolsProps = HTMLAttributes<HTMLDivElement>;

/**
 * Container for toolbar buttons and controls within the prompt input.
 * Provides consistent horizontal layout with small gaps between tool elements.
 *
 * @param className Optional additional CSS classes.
 * @param props Additional HTML div element props.
 * @returns Flex container for tool buttons and controls.
 */
export const PromptInputTools = ({ className, ...props }: PromptInputToolsProps) => (
  <div className={cn("flex items-center gap-1", className)} {...props} />
);

/**
 * Props for the PromptInputButton component.
 */
export type PromptInputButtonProps = ComponentProps<typeof InputGroupButton>;

/**
 * Button component for prompt input toolbars.
 * Adjusts size based on content for consistent appearance.
 *
 * @param variant Button variant. Defaults to "ghost".
 * @param className Optional additional CSS classes.
 * @param size Optional explicit size. Auto-calculated if not provided.
 * @param props Additional button props.
 * @returns InputGroupButton with size auto-adjustment based on children count.
 */
export const PromptInputButton = ({
  variant = "ghost",
  className,
  size,
  ...props
}: PromptInputButtonProps) => {
  const newSize = size ?? (Children.count(props.children) > 1 ? "sm" : "icon-sm");

  return (
    <InputGroupButton
      className={cn(className)}
      size={newSize}
      type="button"
      variant={variant}
      {...props}
    />
  );
};

/**
 * Props for the PromptInputActionMenu component.
 */
export type PromptInputActionMenuProps = ComponentProps<typeof DropdownMenu>;
export const PromptInputActionMenu = (props: PromptInputActionMenuProps) => (
  <DropdownMenu {...props} />
);

/**
 * Props for the PromptInputActionMenuTrigger component.
 */
export type PromptInputActionMenuTriggerProps = PromptInputButtonProps;

export const PromptInputActionMenuTrigger = ({
  className,
  children,
  ...props
}: PromptInputActionMenuTriggerProps) => (
  <DropdownMenuTrigger asChild>
    <PromptInputButton className={className} {...props}>
      {children ?? <PlusIcon className="size-4" />}
    </PromptInputButton>
  </DropdownMenuTrigger>
);

/**
 * Props for the PromptInputActionMenuContent component.
 */
export type PromptInputActionMenuContentProps = ComponentProps<
  typeof DropdownMenuContent
>;
export const PromptInputActionMenuContent = ({
  className,
  ...props
}: PromptInputActionMenuContentProps) => (
  <DropdownMenuContent align="start" className={cn(className)} {...props} />
);

/**
 * Props for the PromptInputActionMenuItem component.
 */
export type PromptInputActionMenuItemProps = ComponentProps<typeof DropdownMenuItem>;
export const PromptInputActionMenuItem = ({
  className,
  ...props
}: PromptInputActionMenuItemProps) => (
  <DropdownMenuItem className={cn(className)} {...props} />
);

// Note: Actions that perform side-effects (like opening a file dialog)
// are provided in opt-in modules (e.g., prompt-input-attachments).

/**
 * Props for the PromptInputSubmit component.
 */
export type PromptInputSubmitProps = ComponentProps<typeof InputGroupButton> & {
  /** Current chat status to determine icon display. */
  status?: ChatStatus;
};

export const PromptInputSubmit = ({
  className,
  variant = "default",
  size = "icon-sm",
  status,
  children,
  ...props
}: PromptInputSubmitProps) => {
  let Icon = <SendIcon className="size-4" />;

  if (status === "submitted") {
    Icon = <Loader2Icon className="size-4 animate-spin" />;
  } else if (status === "streaming") {
    Icon = <SquareIcon className="size-4" />;
  } else if (status === "error") {
    Icon = <XIcon className="size-4" />;
  }

  return (
    <InputGroupButton
      aria-label="Submit"
      className={cn(className)}
      size={size}
      type="submit"
      variant={variant}
      {...props}
    >
      {children ?? Icon}
    </InputGroupButton>
  );
};

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  onstart: ((this: SpeechRecognition, ev: Event) => any) | null;
  onend: ((this: SpeechRecognition, ev: Event) => any) | null;
  onresult: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => any) | null;
  onerror: ((this: SpeechRecognition, ev: SpeechRecognitionErrorEvent) => any) | null;
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
}

type SpeechRecognitionResultList = {
  readonly length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
};

type SpeechRecognitionResult = {
  readonly length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
  isFinal: boolean;
};

type SpeechRecognitionAlternative = {
  transcript: string;
  confidence: number;
};

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
}

declare global {
  interface Window {
    SpeechRecognition: {
      new (): SpeechRecognition;
    };
    webkitSpeechRecognition: {
      new (): SpeechRecognition;
    };
  }
}

/**
 * Props for the PromptInputSpeechButton component.
 */
export type PromptInputSpeechButtonProps = ComponentProps<typeof PromptInputButton> & {
  /** Reference to the textarea element for transcription insertion. */
  textareaRef?: RefObject<HTMLTextAreaElement | null>;
  /** Callback fired when transcription text changes. */
  onTranscriptionChange?: (text: string) => void;
};

export const PromptInputSpeechButton = ({
  className,
  textareaRef,
  onTranscriptionChange,
  ...props
}: PromptInputSpeechButtonProps) => {
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<SpeechRecognition | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    if (
      typeof window !== "undefined" &&
      ("SpeechRecognition" in window || "webkitSpeechRecognition" in window)
    ) {
      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;
      const speechRecognition = new SpeechRecognition();

      speechRecognition.continuous = true;
      speechRecognition.interimResults = true;
      speechRecognition.lang = "en-US";

      speechRecognition.onstart = () => {
        setIsListening(true);
      };

      speechRecognition.onend = () => {
        setIsListening(false);
      };

      speechRecognition.onresult = (event) => {
        let finalTranscript = "";

        const results = Array.from(event.results);

        for (const result of results) {
          if (result.isFinal) {
            finalTranscript += result[0]?.transcript ?? "";
          }
        }

        if (finalTranscript && textareaRef?.current) {
          const textarea = textareaRef.current;
          const currentValue = textarea.value;
          const newValue = currentValue + (currentValue ? " " : "") + finalTranscript;

          textarea.value = newValue;
          textarea.dispatchEvent(new Event("input", { bubbles: true }));
          onTranscriptionChange?.(newValue);
        }
      };

      speechRecognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        setIsListening(false);
      };

      recognitionRef.current = speechRecognition;
      setRecognition(speechRecognition);
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, [textareaRef, onTranscriptionChange]);

  // Toggles speech recognition on/off based on current listening state
  const toggleListening = useCallback(() => {
    if (!recognition) {
      return;
    }

    if (isListening) {
      recognition.stop();
    } else {
      recognition.start();
    }
  }, [recognition, isListening]);

  return (
    <PromptInputButton
      className={cn(
        "relative transition-all duration-200",
        isListening && "animate-pulse bg-accent text-accent-foreground",
        className
      )}
      disabled={!recognition}
      onClick={toggleListening}
      {...props}
    >
      <MicIcon className="size-4" />
    </PromptInputButton>
  );
};

/**
 * Props for the PromptInputModelSelect component.
 */
export type PromptInputModelSelectProps = ComponentProps<typeof Select>;

/**
 * Prompt input model select component for the AI chat UI.
 *
 * @param props Additional props.
 * @returns A select with the prompt input model.
 */
export const PromptInputModelSelect = (props: PromptInputModelSelectProps) => (
  <Select {...props} />
);

/**
 * Props for the PromptInputModelSelectTrigger component.
 */
export type PromptInputModelSelectTriggerProps = ComponentProps<typeof SelectTrigger>;

/**
 * Prompt input model select trigger component for the AI chat UI.
 *
 * @param className Optional extra classes.
 * @param props Additional props.
 * @returns A select trigger with the prompt input model.
 */
export const PromptInputModelSelectTrigger = ({
  className,
  ...props
}: PromptInputModelSelectTriggerProps) => (
  <SelectTrigger
    className={cn(
      "border-none bg-transparent font-medium text-muted-foreground shadow-none transition-colors",
      "hover:bg-accent hover:text-foreground aria-expanded:bg-accent aria-expanded:text-foreground",
      className
    )}
    {...props}
  />
);

/**
 * Props for the PromptInputModelSelectContent component.
 */
export type PromptInputModelSelectContentProps = ComponentProps<typeof SelectContent>;

/**
 * Prompt input model select content component for the AI chat UI.
 *
 * @param className Optional extra classes.
 * @param props Additional props.
 * @returns A select content with the prompt input model.
 */
export const PromptInputModelSelectContent = ({
  className,
  ...props
}: PromptInputModelSelectContentProps) => (
  <SelectContent className={cn(className)} {...props} />
);

/**
 * Props for the PromptInputModelSelectItem component.
 */
export type PromptInputModelSelectItemProps = ComponentProps<typeof SelectItem>;

/**
 * Prompt input model select item component for the AI chat UI.
 *
 * @param className Optional extra classes.
 * @param props Additional props.
 * @returns A select item with the prompt input model.
 */
export const PromptInputModelSelectItem = ({
  className,
  ...props
}: PromptInputModelSelectItemProps) => (
  <SelectItem className={cn(className)} {...props} />
);

/**
 * Props for the PromptInputModelSelectValue component.
 */
export type PromptInputModelSelectValueProps = ComponentProps<typeof SelectValue>;

/**
 * Prompt input model select value component for the AI chat UI.
 *
 * @param className Optional extra classes.
 * @param props Additional props.
 * @returns A select value with the prompt input model.
 */
export const PromptInputModelSelectValue = ({
  className,
  ...props
}: PromptInputModelSelectValueProps) => (
  <SelectValue className={cn(className)} {...props} />
);

/**
 * Props for the PromptInputHoverCard component.
 */
export type PromptInputHoverCardProps = ComponentProps<typeof HoverCard>;

/**
 * Prompt input hover card component for the AI chat UI.
 *
 * @param openDelay Open delay.
 * @param closeDelay Close delay.
 * @param props Additional props.
 * @returns A hover card with the prompt input.
 */
export const PromptInputHoverCard = ({
  openDelay = 0,
  closeDelay = 0,
  ...props
}: PromptInputHoverCardProps) => (
  <HoverCard closeDelay={closeDelay} openDelay={openDelay} {...props} />
);

/**
 * Props for the PromptInputHoverCardTrigger component.
 */
export type PromptInputHoverCardTriggerProps = ComponentProps<typeof HoverCardTrigger>;

/**
 * Prompt input hover card trigger component for the AI chat UI.
 *
 * @param props Additional props.
 * @returns A hover card trigger with the prompt input.
 */
export const PromptInputHoverCardTrigger = (
  props: PromptInputHoverCardTriggerProps
) => <HoverCardTrigger {...props} />;

/**
 * Props for the PromptInputHoverCardContent component.
 */
export type PromptInputHoverCardContentProps = ComponentProps<typeof HoverCardContent>;

/**
 * Prompt input hover card content component for the AI chat UI.
 *
 * @param align Alignment.
 * @param props Additional props.
 * @returns A hover card content with the prompt input.
 */
export const PromptInputHoverCardContent = ({
  align = "start",
  ...props
}: PromptInputHoverCardContentProps) => <HoverCardContent align={align} {...props} />;

/**
 * Props for the PromptInputTabsList component.
 */
export type PromptInputTabsListProps = HTMLAttributes<HTMLDivElement>;

/**
 * Prompt input tabs list component for the AI chat UI.
 *
 * @param className Optional extra classes.
 * @param props Additional props.
 * @returns A div with the prompt input tabs list.
 */
export const PromptInputTabsList = ({
  className,
  ...props
}: PromptInputTabsListProps) => <div className={cn(className)} {...props} />;

/**
 * Props for the PromptInputTab component.
 */
export type PromptInputTabProps = HTMLAttributes<HTMLDivElement>;

/**
 * Prompt input tab component for the AI chat UI.
 *
 * @param className Optional extra classes.
 * @param props Additional props.
 * @returns A div with the prompt input tab.
 */
export const PromptInputTab = ({ className, ...props }: PromptInputTabProps) => (
  <div className={cn(className)} {...props} />
);

/**
 * Props for the PromptInputTabLabel component.
 */
export type PromptInputTabLabelProps = HTMLAttributes<HTMLHeadingElement>;

/**
 * Prompt input tab label component for the AI chat UI.
 *
 * @param className Optional extra classes.
 * @param props Additional props.
 * @returns A h3 with the prompt input tab label.
 */
export const PromptInputTabLabel = ({
  className,
  ...props
}: PromptInputTabLabelProps) => (
  <h3
    className={cn("mb-2 px-3 font-medium text-muted-foreground text-xs", className)}
    {...props}
  />
);

/**
 * Props for the PromptInputTabBody component.
 */
export type PromptInputTabBodyProps = HTMLAttributes<HTMLDivElement>;

/**
 * Prompt input tab body component for the AI chat UI.
 *
 * @param className Optional extra classes.
 * @param props Additional props.
 * @returns A div with the prompt input tab body.
 */
export const PromptInputTabBody = ({
  className,
  ...props
}: PromptInputTabBodyProps) => (
  <div className={cn("space-y-1", className)} {...props} />
);

/**
 * Props for the PromptInputTabItem component.
 */
export type PromptInputTabItemProps = HTMLAttributes<HTMLDivElement>;

/**
 * Prompt input tab item component for the AI chat UI.
 *
 * @param className Optional extra classes.
 * @param props Additional props.
 * @returns A div with the prompt input tab item.
 */
export const PromptInputTabItem = ({
  className,
  ...props
}: PromptInputTabItemProps) => (
  <div
    className={cn(
      "flex items-center gap-2 px-3 py-2 text-xs hover:bg-accent",
      className
    )}
    {...props}
  />
);

/**
 * Props for the PromptInputCommand component.
 */
export type PromptInputCommandProps = ComponentProps<typeof Command>;

/**
 * Prompt input command component for the AI chat UI.
 *
 * @param className Optional extra classes.
 * @param props Additional props.
 * @returns A command with the prompt input.
 */
export const PromptInputCommand = ({
  className,
  ...props
}: PromptInputCommandProps) => <Command className={cn(className)} {...props} />;

/**
 * Props for the PromptInputCommandInput component.
 */
export type PromptInputCommandInputProps = ComponentProps<typeof CommandInput>;

/**
 * Prompt input command input component for the AI chat UI.
 *
 * @param className Optional extra classes.
 * @param props Additional props.
 * @returns A command input with the prompt input.
 */
export const PromptInputCommandInput = ({
  className,
  ...props
}: PromptInputCommandInputProps) => (
  <CommandInput className={cn(className)} {...props} />
);

/**
 * Props for the PromptInputCommandList component.
 */
export type PromptInputCommandListProps = ComponentProps<typeof CommandList>;

/**
 * Prompt input command list component for the AI chat UI.
 *
 * @param className Optional extra classes.
 * @param props Additional props.
 * @returns A command list with the prompt input.
 */
export const PromptInputCommandList = ({
  className,
  ...props
}: PromptInputCommandListProps) => <CommandList className={cn(className)} {...props} />;

/**
 * Props for the PromptInputCommandEmpty component.
 */
export type PromptInputCommandEmptyProps = ComponentProps<typeof CommandEmpty>;

/**
 * Prompt input command empty component for the AI chat UI.
 *
 * @param className Optional extra classes.
 * @param props Additional props.
 * @returns A command empty with the prompt input.
 */
export const PromptInputCommandEmpty = ({
  className,
  ...props
}: PromptInputCommandEmptyProps) => (
  <CommandEmpty className={cn(className)} {...props} />
);

/**
 * Props for the PromptInputCommandGroup component.
 */
export type PromptInputCommandGroupProps = ComponentProps<typeof CommandGroup>;

/**
 * Prompt input command group component for the AI chat UI.
 *
 * @param className Optional extra classes.
 * @param props Additional props.
 * @returns A command group with the prompt input.
 */
export const PromptInputCommandGroup = ({
  className,
  ...props
}: PromptInputCommandGroupProps) => (
  <CommandGroup className={cn(className)} {...props} />
);

/**
 * Props for the PromptInputCommandItem component.
 */
export type PromptInputCommandItemProps = ComponentProps<typeof CommandItem>;

/**
 * Prompt input command item component for the AI chat UI.
 *
 * @param className Optional extra classes.
 * @param props Additional props.
 * @returns A command item with the prompt input.
 */
export const PromptInputCommandItem = ({
  className,
  ...props
}: PromptInputCommandItemProps) => <CommandItem className={cn(className)} {...props} />;

/**
 * Props for the PromptInputCommandSeparator component.
 */
export type PromptInputCommandSeparatorProps = ComponentProps<typeof CommandSeparator>;

/**
 * Prompt input command separator component for the AI chat UI.
 *
 * @param className Optional extra classes.
 * @param props Additional props.
 * @returns A command separator with the prompt input.
 */
export const PromptInputCommandSeparator = ({
  className,
  ...props
}: PromptInputCommandSeparatorProps) => (
  <CommandSeparator className={cn(className)} {...props} />
);
