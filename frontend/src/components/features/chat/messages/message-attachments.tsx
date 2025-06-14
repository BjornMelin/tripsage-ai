"use client";

import { FileArchiveIcon, FileIcon, FileTextIcon, ImageIcon } from "lucide-react";
import Image from "next/image";
import React from "react";

interface MessageAttachmentsProps {
  attachments: string[];
}

export function MessageAttachments({ attachments }: MessageAttachmentsProps) {
  if (!attachments || attachments.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {attachments.map((url, index) => (
        <AttachmentItem key={`attachment-${url}-${index}`} url={url} />
      ))}
    </div>
  );
}

interface AttachmentItemProps {
  url: string;
}

function AttachmentItem({ url }: AttachmentItemProps) {
  // Extract file name from URL
  const fileName = url.split("/").pop() || "File";

  // Determine file type from extension
  const fileExt = fileName.split(".").pop()?.toLowerCase() || "";

  const isImage = ["jpg", "jpeg", "png", "gif", "webp", "svg"].includes(fileExt);
  const isPDF = fileExt === "pdf";
  const isText = [
    "txt",
    "md",
    "csv",
    "json",
    "xml",
    "html",
    "js",
    "ts",
    "css",
  ].includes(fileExt);
  const isArchive = ["zip", "rar", "7z", "tar", "gz"].includes(fileExt);

  const handleClick = () => {
    window.open(url, "_blank");
  };

  if (isImage) {
    return (
      <div
        className="relative h-40 w-40 overflow-hidden rounded-md border bg-background cursor-pointer"
        onClick={handleClick}
      >
        <Image src={url} alt={fileName} fill className="object-cover" />
      </div>
    );
  }

  if (isPDF) {
    return (
      <div
        className="flex items-center gap-2 rounded-md border bg-background p-2 cursor-pointer hover:bg-secondary/50"
        onClick={handleClick}
      >
        <FileIcon className="h-5 w-5 text-red-500" />
        <span className="text-sm truncate max-w-[200px]">{fileName}</span>
      </div>
    );
  }

  if (isText) {
    return (
      <div
        className="flex items-center gap-2 rounded-md border bg-background p-2 cursor-pointer hover:bg-secondary/50"
        onClick={handleClick}
      >
        <FileTextIcon className="h-5 w-5 text-blue-500" />
        <span className="text-sm truncate max-w-[200px]">{fileName}</span>
      </div>
    );
  }

  if (isArchive) {
    return (
      <div
        className="flex items-center gap-2 rounded-md border bg-background p-2 cursor-pointer hover:bg-secondary/50"
        onClick={handleClick}
      >
        <FileArchiveIcon className="h-5 w-5 text-yellow-500" />
        <span className="text-sm truncate max-w-[200px]">{fileName}</span>
      </div>
    );
  }

  return (
    <div
      className="flex items-center gap-2 rounded-md border bg-background p-2 cursor-pointer hover:bg-secondary/50"
      onClick={handleClick}
    >
      <FileIcon className="h-5 w-5" />
      <span className="text-sm truncate max-w-[200px]">{fileName}</span>
    </div>
  );
}
