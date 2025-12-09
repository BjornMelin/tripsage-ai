/**
 * @fileoverview Shared media/attachment primitives.
 */

import { z } from "zod";

export const ATTACHMENT_SCHEMA = z.object({
  contentType: z.string().optional(),
  id: z.string(),
  name: z.string().optional(),
  size: z.number().optional(),
  url: z.string(),
});

export type Attachment = z.infer<typeof ATTACHMENT_SCHEMA>;
