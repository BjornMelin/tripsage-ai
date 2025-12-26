/**
 * @fileoverview Bounded request body readers to enforce hard size limits before parsing.
 */

export class PayloadTooLargeError extends Error {
  readonly maxBytes: number;

  constructor(maxBytes: number) {
    super("payload_too_large");
    Object.setPrototypeOf(this, new.target.prototype);
    this.name = "PayloadTooLargeError";
    this.maxBytes = maxBytes;
  }
}

export class RequestBodyAlreadyReadError extends Error {
  constructor() {
    super("request_body_already_read");
    Object.setPrototypeOf(this, new.target.prototype);
    this.name = "RequestBodyAlreadyReadError";
  }
}

function parseContentLength(headers: Headers): number | null {
  const raw = headers.get("content-length")?.trim();
  if (!raw) return null;
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 0) return null;
  return parsed;
}

export async function readRequestBodyBytesWithLimit(
  req: Request,
  maxBytes: number
): Promise<Uint8Array> {
  if (req.bodyUsed) {
    throw new RequestBodyAlreadyReadError();
  }

  const contentLength = parseContentLength(req.headers);
  if (contentLength != null && contentLength > maxBytes) {
    throw new PayloadTooLargeError(maxBytes);
  }

  if (!req.body) return new Uint8Array();

  const reader = req.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (!value) continue;

      const nextTotal = total + value.byteLength;
      if (nextTotal > maxBytes) {
        // Best-effort cancel; do not await (can hang depending on stream impl).
        reader.cancel("payload_too_large").catch(() => {
          // ignore cancel errors
        });
        throw new PayloadTooLargeError(maxBytes);
      }

      chunks.push(value);
      total = nextTotal;
    }
  } finally {
    reader.releaseLock();
  }

  if (chunks.length === 0) return new Uint8Array();

  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return bytes;
}

export async function parseFormDataWithLimit(
  req: Request,
  maxBytes: number
): Promise<FormData> {
  const bytes = await readRequestBodyBytesWithLimit(req, maxBytes);
  if (bytes.byteLength === 0) return new FormData();

  // Avoid `new Headers(req.headers)` due to cross-implementation incompatibilities
  // in some test environments (e.g., MSW's fetch/Headers polyfills).
  const headers = new Headers();
  req.headers.forEach((value, key) => {
    headers.set(key, value);
  });
  // Avoid stale lengths when reconstructing.
  headers.delete("content-length");

  // Avoid DOM lib typing issues (`BodyInit` expects `ArrayBuffer`, not `Uint8Array<ArrayBufferLike>`).
  // Also avoids `SharedArrayBuffer` incompatibilities in the DOM lib types.
  const body = new ArrayBuffer(bytes.byteLength);
  new Uint8Array(body).set(bytes);

  const wrapped = new Request(req.url, {
    body,
    headers,
    method: req.method,
  });

  return wrapped.formData();
}
