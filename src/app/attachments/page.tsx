type AttachmentItem = {
  id: string;
  filename?: string;
  name?: string;
  fileSize?: number;
  mimeType?: string;
};

import { requireUser } from "@/lib/auth/server";
import { getClientEnvVarWithFallback } from "@/lib/env/client";

async function fetchAttachments() {
  const basePath = getClientEnvVarWithFallback("NEXT_PUBLIC_BASE_PATH", "");
  const res = await fetch(`${basePath}/api/attachments/files`, {
    // This is an SSR fetch; the underlying route uses next: { tags: ['attachments'] }.
    cache: "force-cache",
  });
  if (!res.ok) throw new Error("Failed to load attachments");
  return (await res.json()) as { files: AttachmentItem[]; total: number };
}

export default async function AttachmentsPage() {
  // Require authentication for viewing user-specific attachments metadata.
  await requireUser({ redirectTo: "/attachments" });

  const data = await fetchAttachments();
  const files = data.files ?? [];

  return (
    <div style={{ padding: 16 }}>
      <h1>Attachments</h1>
      <p>
        This list is server-rendered and tagged via the API route with
        <code>attachments</code>. Successful uploads call
        <code>revalidateTag('attachments', 'max')</code> to refresh this list on the
        next view.
      </p>
      {files.length === 0 ? (
        <p>No attachments.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th align="left">ID</th>
              <th align="left">Name</th>
              <th align="left">Type</th>
              <th align="right">Size</th>
            </tr>
          </thead>
          <tbody>
            {files.map((f) => (
              <tr key={f.id}>
                <td>{f.id}</td>
                <td>{f.filename ?? f.name ?? "(unnamed)"}</td>
                <td>{f.mimeType ?? ""}</td>
                <td align="right">{f.fileSize ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
