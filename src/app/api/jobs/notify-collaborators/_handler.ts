/**
 * @fileoverview Pure handler for collaborator notification jobs.
 */

import "server-only";

import type { NotifyJob } from "@schemas/webhooks";
import { releaseKey, tryReserveKey } from "@/lib/idempotency/redis";
import type { sendCollaboratorNotifications } from "@/lib/notifications/collaborators";

export interface NotifyCollaboratorsJobDeps {
  sendNotifications: typeof sendCollaboratorNotifications;
}

export async function handleNotifyCollaboratorsJob(
  deps: NotifyCollaboratorsJobDeps,
  job: NotifyJob
): Promise<{ ok: true; duplicate?: true } & Record<string, unknown>> {
  // De-duplicate at worker level to avoid double-send on retries
  const businessKey = `notify:${job.eventKey}`;
  const unique = await tryReserveKey(businessKey, {
    degradedMode: "fail_closed",
    ttlSeconds: 300,
  });

  if (!unique) {
    return { duplicate: true, ok: true };
  }

  try {
    const result = await deps.sendNotifications(job.payload, job.eventKey);
    return { ok: true, ...result };
  } catch (error) {
    // Best-effort release so QStash retries can re-attempt on transient failures.
    await releaseKey(businessKey, { degradedMode: "fail_open" }).catch(() => undefined);
    throw error;
  }
}
