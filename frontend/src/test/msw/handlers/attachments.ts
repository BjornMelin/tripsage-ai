/**
 * @fileoverview MSW handlers for attachment APIs used in tests.
 */

import type { HttpHandler } from "msw";
import { HttpResponse, http } from "msw";

const attachmentsBase = "http://localhost:8001/api/attachments";

export const attachmentHandlers: HttpHandler[] = [
  http.get(`${attachmentsBase}/files`, () =>
    HttpResponse.json({
      data: [],
      nextOffset: 0,
      total: 0,
    })
  ),

  http.post(`${attachmentsBase}/upload`, () =>
    HttpResponse.json({ id: "file-1", status: "completed" }, { status: 200 })
  ),

  http.post(`${attachmentsBase}/upload/batch`, () =>
    HttpResponse.json(
      {
        ids: ["file-1", "file-2"],
        status: "completed",
      },
      { status: 200 }
    )
  ),
];
