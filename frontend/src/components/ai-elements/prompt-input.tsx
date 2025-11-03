/**
 * @fileoverview Prompt input primitives for AI chat UIs. Provides a flexible input group
 * with attachments support and submission handling. Optimized for Next.js App Router.
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
import Image from "next/image";
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
// ============================================================================
// Provider Context & Types
// ============================================================================

export type AttachmentsContext = {
  files: (FileUIPart & { id: string })[];
  add: (files: File[] | FileList) => void;
  remove: (id: string) => void;
  clear: () => void;
  openFileDialog: () => void;
  fileInputRef: RefObject<HTMLInputElement | null>;
};

export type TextInputContext = {
  value: string;
  setInput: (v: string) => void;
  clear: () => void;
};

export type PromptInputControllerProps = {
  textInput: TextInputContext;
  attachments: AttachmentsContext;
  /** INTERNAL: Allows PromptInput to register its file input + "open" callback */
  __registerFileInput: (
    id: string,
    ref: RefObject<HTMLInputElement | null>,
    open: () => void
  ) => void;
  /** INTERNAL: Allows PromptInput to unregister its file input */
  __unregisterFileInput: (id: string) => void;
};

const PROMPT_INPUT_CONTROLLER = createContext<PromptInputControllerProps | null>(null);
const PROVIDER_ATTACHMENTS_CONTEXT = createContext<AttachmentsContext | null>(null);

/**
 * Access the prompt input controller from a surrounding `PromptInputProvider`.
 *
 * @returns Controller with text input and attachments API.
 * @throws Error when used outside a `PromptInputProvider`.
 */
export const usePromptInputController = () => {
  const ctx = useContext(PROMPT_INPUT_CONTROLLER);
  if (!ctx) {
    throw new Error(
      "Wrap your component inside <PromptInputProvider> to use usePromptInputController()."
    );
  }
  return ctx;
};

// Optional variants (do NOT throw). Useful for dual-mode components.
const USE_OPTIONAL_PROMPT_INPUT_CONTROLLER = () => useContext(PROMPT_INPUT_CONTROLLER);

/**
 * Access attachments from the provider scope.
 *
 * @returns Attachment operations bound to the provider.
 * @throws Error when provider is not present.
 */
export const useProviderAttachments = () => {
  const ctx = useContext(PROVIDER_ATTACHMENTS_CONTEXT);
  if (!ctx) {
    throw new Error(
      "Wrap your component inside <PromptInputProvider> to use useProviderAttachments()."
    );
  }
  return ctx;
};

const USE_OPTIONAL_PROVIDER_ATTACHMENTS = () =>
  useContext(PROVIDER_ATTACHMENTS_CONTEXT);

export type PromptInputProviderProps = PropsWithChildren<{
  initialInput?: string;
}>;

/**
 * Optional global provider that lifts PromptInput state outside of PromptInput.
 * If you don't use it, PromptInput stays fully self-managed.
 *
 * Supports multiple PromptInput components within the same provider. When
 * openFileDialog() is called externally (e.g., via PromptInputActionAddAttachments),
 * it opens the most recently registered input.
 */
export function PromptInputProvider({
  initialInput: initialTextInput = "",
  children,
}: PromptInputProviderProps) {
  // ----- textInput state
  const [textInput, setTextInput] = useState(initialTextInput);
  const clearInput = useCallback(() => setTextInput(""), []);

  // ----- attachments state (global when wrapped)
  const [attachments, setAttachments] = useState<(FileUIPart & { id: string })[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  // Store multiple registered inputs: Map<string, { ref, open }>
  const fileInputsRef = useRef<
    Map<string, { ref: RefObject<HTMLInputElement | null>; open: () => void }>
  >(new Map());

  const add = useCallback((files: File[] | FileList) => {
    const incoming = Array.from(files);
    if (incoming.length === 0) return;

    setAttachments((prev) =>
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
    setAttachments((prev) => {
      const found = prev.find((f) => f.id === id);
      if (found?.url) URL.revokeObjectURL(found.url);
      return prev.filter((f) => f.id !== id);
    });
  }, []);

  const clear = useCallback(() => {
    setAttachments((prev) => {
      for (const f of prev) if (f.url) URL.revokeObjectURL(f.url);
      return [];
    });
  }, []);

  const openFileDialog = useCallback(() => {
    // Open the most recently registered input (last in Map iteration order)
    const entries = Array.from(fileInputsRef.current.entries());
    if (entries.length > 0) {
      const [, { open }] = entries[entries.length - 1];
      open();
    }
  }, []);

  // Helper to update fileInputRef to point to the most recently registered input
  const _updateFileInputRef = useCallback(() => {
    const entries = Array.from(fileInputsRef.current.entries());
    if (entries.length > 0) {
      const [, { ref }] = entries[entries.length - 1];
      fileInputRef.current = ref.current;
    } else {
      fileInputRef.current = null;
    }
  }, []);

  const attachmentsContext = useMemo<AttachmentsContext>(
    () => ({
      add,
      clear,
      fileInputRef,
      files: attachments,
      openFileDialog,
      remove,
    }),
    [attachments, add, remove, clear, openFileDialog]
  );

  const __registerFileInput = useCallback(
    (id: string, ref: RefObject<HTMLInputElement | null>, open: () => void) => {
      fileInputsRef.current.set(id, { open, ref });
    },
    []
  );

  const __unregisterFileInput = useCallback((id: string) => {
    fileInputsRef.current.delete(id);
  }, []);

  const controller = useMemo<PromptInputControllerProps>(
    () => ({
      __registerFileInput,
      __unregisterFileInput,
      attachments: attachmentsContext,
      textInput: {
        clear: clearInput,
        setInput: setTextInput,
        value: textInput,
      },
    }),
    [
      textInput,
      clearInput,
      attachmentsContext,
      __registerFileInput,
      __unregisterFileInput,
    ]
  );

  // Cleanup object URLs on unmount to prevent memory leaks
  useEffect(() => {
    return () => {
      for (const attachment of attachments) {
        if (attachment.url) {
          URL.revokeObjectURL(attachment.url);
        }
      }
    };
  }, [attachments]);

  return (
    <PROMPT_INPUT_CONTROLLER.Provider value={controller}>
      <PROVIDER_ATTACHMENTS_CONTEXT.Provider value={attachmentsContext}>
        {children}
      </PROVIDER_ATTACHMENTS_CONTEXT.Provider>
    </PROMPT_INPUT_CONTROLLER.Provider>
  );
}

// ============================================================================
// Component Context & Hooks
// ============================================================================

const LOCAL_ATTACHMENTS_CONTEXT = createContext<AttachmentsContext | null>(null);

/**
 * Access attachments for the nearest PromptInput or Provider.
 *
 * @returns Attachment operations for the current input.
 * @throws Error if no PromptInput/Provider context is found.
 */
export const usePromptInputAttachments = () => {
  // Dual-mode: prefer provider if present, otherwise use local
  const provider = USE_OPTIONAL_PROVIDER_ATTACHMENTS();
  const local = useContext(LOCAL_ATTACHMENTS_CONTEXT);
  const context = provider ?? local;
  if (!context) {
    throw new Error(
      "usePromptInputAttachments must be used within a PromptInput or PromptInputProvider"
    );
  }
  return context;
};

export type PromptInputAttachmentProps = HTMLAttributes<HTMLDivElement> & {
  data: FileUIPart & { id: string };
  className?: string;
};

/**
 * Visual chip for a single attachment with remove and preview.
 *
 * @param data File metadata to render and manage.
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
                <Image
                  alt={filename || "attachment"}
                  className="size-5 object-cover"
                  height={20}
                  src={data.url}
                  width={20}
                  unoptimized
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
              <Image
                alt={filename || "attachment preview"}
                className="max-h-full max-w-full object-contain"
                height={384}
                src={data.url}
                width={448}
                unoptimized
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

export type PromptInputAttachmentsProps = Omit<
  HTMLAttributes<HTMLDivElement>,
  "children"
> & {
  children: (attachment: FileUIPart & { id: string }) => ReactNode;
};

export function PromptInputAttachments({ children }: PromptInputAttachmentsProps) {
  const attachments = usePromptInputAttachments();

  if (!attachments.files.length) {
    return null;
  }

  return attachments.files.map((file) => (
    <Fragment key={file.id}>{children(file)}</Fragment>
  ));
}

export type PromptInputActionAddAttachmentsProps = ComponentProps<
  typeof DropdownMenuItem
> & {
  label?: string;
};

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

export type PromptInputMessage = {
  text?: string;
  files?: FileUIPart[];
};

export type PromptInputProps = Omit<
  HTMLAttributes<HTMLFormElement>,
  "onSubmit" | "onError"
> & {
  accept?: string; // e.g., "image/*" or leave undefined for any
  multiple?: boolean;
  // When true, accepts drops anywhere on document. Default false (opt-in).
  globalDrop?: boolean;
  // Render a hidden input with given name and keep it in sync for native form posts. Default false.
  syncHiddenInput?: boolean;
  // Minimal constraints
  maxFiles?: number;
  maxFileSize?: number; // bytes
  onError?: (err: {
    code:
      | "max_files"
      | "max_file_size"
      | "accept"
      | "submission_failed"
      | "file_conversion_failed";
    message: string;
  }) => void;
  onSubmit: (
    message: PromptInputMessage,
    event: FormEvent<HTMLFormElement>
  ) => void | Promise<void>;
};

/**
 * Main prompt input form with drag-and-drop, paste, and attachments.
 *
 * @param onSubmit Called with text and files; can be async.
 * @param onError Optional error handler for constraints.
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
  const controller = USE_OPTIONAL_PROMPT_INPUT_CONTROLLER();
  const usingProvider = !!controller;

  // Refs
  const inputRef = useRef<HTMLInputElement | null>(null);
  const anchorRef = useRef<HTMLSpanElement>(null);
  const formRef = useRef<HTMLFormElement | null>(null);
  const inputIdRef = useRef<string>(`prompt-input-${nanoid()}`);

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

  const openFileDialogLocal = useCallback(() => {
    inputRef.current?.click();
  }, []);

  const matchesAccept = useCallback(
    (f: File) => {
      if (!accept || accept.trim() === "") {
        return true;
      }
      // Split accept string by comma and trim each entry
      const acceptList = accept
        .split(",")
        .map((a) => a.trim())
        .filter(Boolean);

      // Check each accept entry
      for (const entry of acceptList) {
        if (entry === "*/*") {
          return true;
        }
        if (entry.endsWith("/*")) {
          // MIME type group, e.g. "image/*"
          const group = entry.split("/")[0];
          if (f.type.startsWith(`${group}/`)) {
            return true;
          }
        } else if (entry.startsWith(".")) {
          // File extension, e.g. ".pdf"
          if (f.name.toLowerCase().endsWith(entry.toLowerCase())) {
            return true;
          }
        } else {
          // Specific MIME type, e.g. "application/pdf"
          if (f.type === entry) {
            return true;
          }
        }
      }
      // No match found
      return false;
    },
    [accept]
  );

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

    const inputId = inputIdRef.current;
    controller.__registerFileInput(inputId, inputRef, () => inputRef.current?.click());

    return () => {
      controller.__unregisterFileInput(inputId);
    };
  }, [usingProvider, controller, inputRef]);

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

  const MaxBlobSize = 5 * 1024 * 1024; // 5MB

  const convertBlobUrlToDataUrl = async (url: string): Promise<string> => {
    const response = await fetch(url);
    const blob = await response.blob();

    if (blob.size > MaxBlobSize) {
      throw new Error(
        `File is too large to convert. Please select a file smaller than ${MaxBlobSize / (1024 * 1024)}MB.`
      );
    }

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

    // Convert blob URLs to data URLs asynchronously
    Promise.all(
      files.map(async ({ id, ...item }) => {
        if (item.url?.startsWith("blob:")) {
          try {
            return {
              ...item,
              url: await convertBlobUrlToDataUrl(item.url),
            };
          } catch (error) {
            // Handle individual file conversion errors
            const errorMessage =
              error instanceof Error ? error.message : "Unknown conversion error";
            onError?.({
              code: "file_conversion_failed",
              message: `Failed to process file "${item.filename || "unknown"}": ${errorMessage}`,
            });
            // Return the original item without conversion
            return item;
          }
        }
        return item;
      })
    )
      .then((convertedFiles: FileUIPart[]) => {
        try {
          const result = onSubmit({ files: convertedFiles, text }, event);

          // Handle both sync and async onSubmit
          if (result instanceof Promise) {
            result
              .then(() => {
                clear();
                if (usingProvider) {
                  controller.textInput.clear();
                } else {
                  form.reset();
                }
              })
              .catch((_error) => {
                // Don't clear on error - user may want to retry
                onError?.({
                  code: "submission_failed",
                  message: "Failed to submit prompt. Please try again.",
                });
              });
          } else {
            // Sync function completed without throwing, clear attachments
            clear();
            if (usingProvider) {
              controller.textInput.clear();
            } else {
              form.reset();
            }
          }
        } catch (_error) {
          // Don't clear on error - user may want to retry
          onError?.({
            code: "submission_failed",
            message: "Failed to submit prompt. Please try again.",
          });
        }
      })
      .catch((_error) => {
        // General error in Promise.all - this shouldn't happen with our individual error handling
        onError?.({
          code: "file_conversion_failed",
          message: "Failed to process files. Please try again.",
        });
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
    <LOCAL_ATTACHMENTS_CONTEXT.Provider value={ctx}>
      {inner}
    </LOCAL_ATTACHMENTS_CONTEXT.Provider>
  );
};

export type PromptInputBodyProps = HTMLAttributes<HTMLDivElement>;

/** Body content wrapper inside the input group. */
export const PromptInputBody = ({ className, ...props }: PromptInputBodyProps) => (
  <div className={cn("contents", className)} {...props} />
);

export type PromptInputTextareaProps = ComponentProps<typeof InputGroupTextarea> & {
  accept?: string;
};

/** Multiline text control for entering prompts. Handles Enter to submit. */
export const PromptInputTextarea = ({
  onChange,
  className,
  placeholder = "What would you like to know?",
  accept,
  ...props
}: PromptInputTextareaProps) => {
  const controller = USE_OPTIONAL_PROMPT_INPUT_CONTROLLER();
  const attachments = usePromptInputAttachments();
  const [isComposing, setIsComposing] = useState(false);

  const matchesAccept = useCallback(
    (f: File) => {
      if (!accept || accept.trim() === "") {
        return true;
      }
      // Split accept string by comma and trim each entry
      const acceptList = accept
        .split(",")
        .map((a) => a.trim())
        .filter(Boolean);

      // Check each accept entry
      for (const entry of acceptList) {
        if (entry === "*/*") {
          return true;
        }
        if (entry.endsWith("/*")) {
          // MIME type group, e.g. "image/*"
          const group = entry.split("/")[0];
          if (f.type.startsWith(`${group}/`)) {
            return true;
          }
        } else if (entry.startsWith(".")) {
          // File extension, e.g. ".pdf"
          if (f.name.toLowerCase().endsWith(entry.toLowerCase())) {
            return true;
          }
        } else {
          // Specific MIME type, e.g. "application/pdf"
          if (f.type === entry) {
            return true;
          }
        }
      }
      // No match found
      return false;
    },
    [accept]
  );

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

  const handlePaste: ClipboardEventHandler<HTMLTextAreaElement> = (event) => {
    const items = event.clipboardData?.items;

    if (!items) {
      return;
    }

    const acceptedFiles: File[] = [];
    const rejectedFiles: File[] = [];

    for (const item of items) {
      if (item.kind === "file") {
        const file = item.getAsFile();
        if (file) {
          if (matchesAccept(file)) {
            acceptedFiles.push(file);
          } else {
            rejectedFiles.push(file);
          }
        }
      }
    }

    if (acceptedFiles.length > 0) {
      event.preventDefault();
      attachments.add(acceptedFiles);
    }

    if (rejectedFiles.length > 0) {
      // Log rejected files for debugging - in a real implementation,
      // you might want to use a toast notification or other UI feedback
      console.warn(
        `Rejected pasted files: ${rejectedFiles.map((f) => f.name).join(", ")}`
      );
    }
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

export type PromptInputHeaderProps = Omit<
  ComponentProps<typeof InputGroupAddon>,
  "align"
>;

/** Header addon row for prompt input. */
export const PromptInputHeader = ({ className, ...props }: PromptInputHeaderProps) => (
  <InputGroupAddon
    align="block-end"
    className={cn("order-first flex-wrap gap-1", className)}
    {...props}
  />
);

export type PromptInputFooterProps = Omit<
  ComponentProps<typeof InputGroupAddon>,
  "align"
>;

/** Footer addon row for prompt input. */
export const PromptInputFooter = ({ className, ...props }: PromptInputFooterProps) => (
  <InputGroupAddon
    align="block-end"
    className={cn("justify-between gap-1", className)}
    {...props}
  />
);

export type PromptInputToolsProps = HTMLAttributes<HTMLDivElement>;

/** Container for tool buttons within header/footer. */
export const PromptInputTools = ({ className, ...props }: PromptInputToolsProps) => (
  <div className={cn("flex items-center gap-1", className)} {...props} />
);

export type PromptInputButtonProps = ComponentProps<typeof InputGroupButton>;

/** Button styled for usage within prompt input groups. */
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

export type PromptInputActionMenuProps = ComponentProps<typeof DropdownMenu>;
/** Dropdown menu wrapper for prompt actions. */
export const PromptInputActionMenu = (props: PromptInputActionMenuProps) => (
  <DropdownMenu {...props} />
);

export type PromptInputActionMenuTriggerProps = PromptInputButtonProps;

/** Trigger for the prompt action dropdown menu. */
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

export type PromptInputActionMenuContentProps = ComponentProps<
  typeof DropdownMenuContent
>;
/** Content container for the prompt action dropdown. */
export const PromptInputActionMenuContent = ({
  className,
  ...props
}: PromptInputActionMenuContentProps) => (
  <DropdownMenuContent align="start" className={cn(className)} {...props} />
);

export type PromptInputActionMenuItemProps = ComponentProps<typeof DropdownMenuItem>;
/** Single item entry for the prompt action dropdown. */
export const PromptInputActionMenuItem = ({
  className,
  ...props
}: PromptInputActionMenuItemProps) => (
  <DropdownMenuItem className={cn(className)} {...props} />
);

// Note: Actions that perform side-effects (like opening a file dialog)
// are provided in opt-in modules (e.g., prompt-input-attachments).

export type PromptInputSubmitProps = ComponentProps<typeof InputGroupButton> & {
  status?: ChatStatus;
};

/** Submit button for the prompt input. */
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

export type PromptInputSpeechButtonProps = ComponentProps<typeof PromptInputButton> & {
  textareaRef?: RefObject<HTMLTextAreaElement | null>;
  onTranscriptionChange?: (text: string) => void;
  speechRecognitionLang?: string; // Optional prop to set speech recognition language
};

export const PromptInputSpeechButton = ({
  className,
  textareaRef,
  onTranscriptionChange,
  speechRecognitionLang,
  ...props
}: PromptInputSpeechButtonProps) => {
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<SpeechRecognition | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const lastProcessedFinalRef = useRef<string>("");

  // Determine language: use prop if provided, otherwise use browser locale or fallback to 'en-US'
  const lang =
    speechRecognitionLang ||
    (typeof navigator !== "undefined" && navigator.language) ||
    "en-US";

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
      speechRecognition.lang = lang;

      speechRecognition.onstart = () => {
        setIsListening(true);
      };

      speechRecognition.onend = () => {
        setIsListening(false);
      };

      speechRecognition.onresult = (event) => {
        let finalTranscript = "";
        let interimTranscript = "";

        const results = Array.from(event.results);

        for (const result of results) {
          if (result.isFinal) {
            finalTranscript += result[0]?.transcript ?? "";
          } else {
            interimTranscript += result[0]?.transcript ?? "";
          }
        }

        if (textareaRef?.current) {
          const textarea = textareaRef.current;

          if (finalTranscript) {
            // Add final transcript permanently
            const currentValue = textarea.value;
            const newValue = currentValue + (currentValue ? " " : "") + finalTranscript;

            textarea.value = newValue;
            lastProcessedFinalRef.current = newValue;
            textarea.dispatchEvent(new Event("input", { bubbles: true }));
            onTranscriptionChange?.(newValue);
          } else if (interimTranscript) {
            // Show interim transcript temporarily
            const currentValue = textarea.value;
            const baseValue = lastProcessedFinalRef.current;
            const newValue =
              baseValue +
              (baseValue && currentValue !== baseValue ? " " : "") +
              interimTranscript;

            // Only update if different to avoid cursor jumps
            if (textarea.value !== newValue) {
              textarea.value = newValue;
              textarea.dispatchEvent(new Event("input", { bubbles: true }));
              onTranscriptionChange?.(newValue);
            }
          }
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
  }, [textareaRef, onTranscriptionChange, lang]);

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

export type PromptInputModelSelectProps = ComponentProps<typeof Select>;

export const PromptInputModelSelect = (props: PromptInputModelSelectProps) => (
  <Select {...props} />
);

export type PromptInputModelSelectTriggerProps = ComponentProps<typeof SelectTrigger>;

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

export type PromptInputModelSelectContentProps = ComponentProps<typeof SelectContent>;

export const PromptInputModelSelectContent = ({
  className,
  ...props
}: PromptInputModelSelectContentProps) => (
  <SelectContent className={cn(className)} {...props} />
);

export type PromptInputModelSelectItemProps = ComponentProps<typeof SelectItem>;

export const PromptInputModelSelectItem = ({
  className,
  ...props
}: PromptInputModelSelectItemProps) => (
  <SelectItem className={cn(className)} {...props} />
);

export type PromptInputModelSelectValueProps = ComponentProps<typeof SelectValue>;

export const PromptInputModelSelectValue = ({
  className,
  ...props
}: PromptInputModelSelectValueProps) => (
  <SelectValue className={cn(className)} {...props} />
);

export type PromptInputHoverCardProps = ComponentProps<typeof HoverCard>;

export const PromptInputHoverCard = ({
  openDelay = 0,
  closeDelay = 0,
  ...props
}: PromptInputHoverCardProps) => (
  <HoverCard closeDelay={closeDelay} openDelay={openDelay} {...props} />
);

export type PromptInputHoverCardTriggerProps = ComponentProps<typeof HoverCardTrigger>;

export const PromptInputHoverCardTrigger = (
  props: PromptInputHoverCardTriggerProps
) => <HoverCardTrigger {...props} />;

export type PromptInputHoverCardContentProps = ComponentProps<typeof HoverCardContent>;

export const PromptInputHoverCardContent = ({
  align = "start",
  ...props
}: PromptInputHoverCardContentProps) => <HoverCardContent align={align} {...props} />;

export type PromptInputTabsListProps = HTMLAttributes<HTMLDivElement>;

export const PromptInputTabsList = ({
  className,
  ...props
}: PromptInputTabsListProps) => <div className={cn(className)} {...props} />;

export type PromptInputTabProps = HTMLAttributes<HTMLDivElement>;

export const PromptInputTab = ({ className, ...props }: PromptInputTabProps) => (
  <div className={cn(className)} {...props} />
);

export type PromptInputTabLabelProps = HTMLAttributes<HTMLHeadingElement>;

export const PromptInputTabLabel = ({
  className,
  ...props
}: PromptInputTabLabelProps) => (
  <h3
    className={cn("mb-2 px-3 font-medium text-muted-foreground text-xs", className)}
    {...props}
  />
);

export type PromptInputTabBodyProps = HTMLAttributes<HTMLDivElement>;

export const PromptInputTabBody = ({
  className,
  ...props
}: PromptInputTabBodyProps) => (
  <div className={cn("space-y-1", className)} {...props} />
);

export type PromptInputTabItemProps = HTMLAttributes<HTMLDivElement>;

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

export type PromptInputCommandProps = ComponentProps<typeof Command>;

export const PromptInputCommand = ({
  className,
  ...props
}: PromptInputCommandProps) => <Command className={cn(className)} {...props} />;

export type PromptInputCommandInputProps = ComponentProps<typeof CommandInput>;

export const PromptInputCommandInput = ({
  className,
  ...props
}: PromptInputCommandInputProps) => (
  <CommandInput className={cn(className)} {...props} />
);

export type PromptInputCommandListProps = ComponentProps<typeof CommandList>;

export const PromptInputCommandList = ({
  className,
  ...props
}: PromptInputCommandListProps) => <CommandList className={cn(className)} {...props} />;

export type PromptInputCommandEmptyProps = ComponentProps<typeof CommandEmpty>;

export const PromptInputCommandEmpty = ({
  className,
  ...props
}: PromptInputCommandEmptyProps) => (
  <CommandEmpty className={cn(className)} {...props} />
);

export type PromptInputCommandGroupProps = ComponentProps<typeof CommandGroup>;

export const PromptInputCommandGroup = ({
  className,
  ...props
}: PromptInputCommandGroupProps) => (
  <CommandGroup className={cn(className)} {...props} />
);

export type PromptInputCommandItemProps = ComponentProps<typeof CommandItem>;

export const PromptInputCommandItem = ({
  className,
  ...props
}: PromptInputCommandItemProps) => <CommandItem className={cn(className)} {...props} />;

export type PromptInputCommandSeparatorProps = ComponentProps<typeof CommandSeparator>;

export const PromptInputCommandSeparator = ({
  className,
  ...props
}: PromptInputCommandSeparatorProps) => (
  <CommandSeparator className={cn(className)} {...props} />
);
